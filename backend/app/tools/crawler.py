from __future__ import annotations

import asyncio
import hashlib
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.core.time import iso_now
from app.tools.base import BaseTool
from app.tools.fixtures import fixture_by_url


class DomainRateLimiter:
    def __init__(self) -> None:
        self._last_seen: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, domain: str, delay_seconds: float) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_seen.get(domain, 0.0)
            if elapsed < delay_seconds:
                await asyncio.sleep(delay_seconds - elapsed)
            self._last_seen[domain] = time.monotonic()


_rate_limiter = DomainRateLimiter()


class WebCrawlerTool(BaseTool):
    name = "web_crawler"
    description = "Fetch and extract public web pages while honoring robots.txt and rate limits."

    async def call(self, input_data: dict) -> dict:
        settings = get_settings()
        url = input_data["url"]
        competitor = input_data.get("competitor", "unknown")
        source_type = input_data.get("source_type", "unknown")

        if url.startswith("offline://"):
            fixture = fixture_by_url(url)
            content = fixture["content"] if fixture else "No fixture content is available for this source."
            title = fixture["title"] if fixture else "Generic offline fixture"
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            return {
                "document": {
                    "url": url,
                    "title": title,
                    "content": content,
                    "content_hash": content_hash,
                    "source_type": source_type,
                    "competitor": competitor,
                    "retrieved_at": iso_now(),
                    "metadata": {"compliance": "offline_fixture_no_network"},
                }
            }

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Unsupported crawl URL: {url}")

        if not await self._allowed_by_robots(url, settings.crawler_user_agent, settings.crawler_robots_timeout_seconds):
            raise PermissionError(f"robots.txt disallows crawling {url}")

        await _rate_limiter.wait(parsed.netloc, settings.crawler_rate_limit_seconds)
        async with httpx.AsyncClient(
            headers={"User-Agent": settings.crawler_user_agent},
            follow_redirects=True,
            timeout=httpx.Timeout(settings.crawler_request_timeout_seconds, connect=5.0),
        ) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if content_type and not is_text_response(content_type):
                    raise ValueError(f"Unsupported crawl content type: {content_type}")
                html, truncated = await read_limited_text(response, settings.crawler_max_html_bytes)

        title, text = self._extract_text(html, settings.crawler_max_text_chars)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return {
            "document": {
                "url": str(response.url),
                "title": title,
                "content": text,
                "content_hash": content_hash,
                "source_type": source_type,
                "competitor": competitor,
                "retrieved_at": iso_now(),
                "metadata": {
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "html_truncated": truncated,
                    "compliance": "robots_checked_rate_limited",
                },
            }
        }

    async def _allowed_by_robots(self, url: str, user_agent: str, timeout_seconds: float) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
                response = await client.get(robots_url)
            if response.status_code >= 400:
                return True
            parser.parse(response.text.splitlines())
            return parser.can_fetch(user_agent, url)
        except httpx.HTTPError:
            return True

    def _extract_text(self, html: str, max_chars: int) -> tuple[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
        for tag in soup(["script", "style", "noscript", "svg", "form", "nav", "footer"]):
            tag.decompose()
        text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
        return title, text[:max_chars]


def is_text_response(content_type: str) -> bool:
    return any(
        marker in content_type
        for marker in (
            "text/html",
            "text/plain",
            "application/xhtml+xml",
            "application/json",
            "application/ld+json",
        )
    )


async def read_limited_text(response: httpx.Response, max_bytes: int) -> tuple[str, bool]:
    chunks: list[bytes] = []
    total = 0
    truncated = False
    async for chunk in response.aiter_bytes():
        remaining = max_bytes - total
        if remaining <= 0:
            truncated = True
            break
        if len(chunk) > remaining:
            chunks.append(chunk[:remaining])
            truncated = True
            break
        chunks.append(chunk)
        total += len(chunk)
    body = b"".join(chunks)
    encoding = response.encoding or "utf-8"
    return body.decode(encoding, errors="replace"), truncated
