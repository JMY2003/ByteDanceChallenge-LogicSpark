from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings, should_simulate
from app.core.time import iso_now
from app.tools.base import BaseTool
from app.tools.fixtures import fixture_results_for, generic_fixture_results_for


SEARCH_REQUEST_TIMEOUT_SECONDS = 20.0


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search public web sources. SIMULATIVE mode uses deterministic public-source fixtures."

    async def call(self, input_data: dict) -> dict:
        settings = get_settings()
        query = input_data.get("query", "")
        competitor = input_data.get("competitor") or query
        requested_source_type = normalize_source_type(input_data.get("source_type", "mixed"))
        max_results = int(input_data.get("max_results") or settings.max_search_results_per_competitor)

        if should_simulate(settings):
            fixtures = fixture_results_for(competitor) or generic_fixture_results_for(competitor, query)
            results = [
                {
                    "url": item["url"],
                    "title": item["title"],
                    "snippet": item["content"][:220],
                    "source_type": item["source_type"],
                    "rank": rank,
                    "query": query,
                    "competitor": competitor,
                    "retrieved_at": iso_now(),
                }
                for rank, item in enumerate(fixtures[:max_results], start=1)
            ]
            return {"search_results": results, "provider": "offline_fixture"}

        provider_results = await self._search_with_configured_provider(settings, query, competitor, requested_source_type, max_results)
        if not provider_results:
            raise RuntimeError(f"Live search returned no results for query: {query}")
        return {"search_results": provider_results, "provider": "configured_search"}

    async def _search_with_configured_provider(
        self,
        settings,
        query: str,
        competitor: str,
        requested_source_type: str,
        max_results: int,
    ) -> list[dict]:
        if settings.serper_api_key:
            results = await self._serper(settings.serper_api_key, query, competitor, requested_source_type, max_results)
            if results:
                return results
        if settings.brave_search_api_key:
            results = await self._brave(settings.brave_search_api_key, query, competitor, requested_source_type, max_results)
            if results:
                return results
        return await self._duckduckgo_html(query, competitor, requested_source_type, max_results)

    async def _serper(self, api_key: str, query: str, competitor: str, source_type: str, max_results: int) -> list[dict]:
        async with httpx.AsyncClient(timeout=SEARCH_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": query, "num": max_results},
            )
            response.raise_for_status()
        organic = response.json().get("organic", [])
        return [
            self._result_from_live_item(rank, item.get("link", ""), item.get("title", ""), item.get("snippet", ""), query, competitor, source_type)
            for rank, item in enumerate(organic[:max_results], start=1)
            if item.get("link")
        ]

    async def _brave(self, api_key: str, query: str, competitor: str, source_type: str, max_results: int) -> list[dict]:
        async with httpx.AsyncClient(timeout=SEARCH_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
                params={"q": query, "count": max_results},
            )
            response.raise_for_status()
        items = response.json().get("web", {}).get("results", [])
        return [
            self._result_from_live_item(rank, item.get("url", ""), item.get("title", ""), item.get("description", ""), query, competitor, source_type)
            for rank, item in enumerate(items[:max_results], start=1)
            if item.get("url")
        ]

    async def _duckduckgo_html(self, query: str, competitor: str, source_type: str, max_results: int) -> list[dict]:
        async with httpx.AsyncClient(
            timeout=SEARCH_REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "CompeteScopeAI/0.1 research preview"},
        ) as client:
            response = await client.get("https://duckduckgo.com/html/", params={"q": query})
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for anchor in soup.select(".result__a"):
            href = normalize_duckduckgo_url(anchor.get("href", ""))
            if not href.startswith(("http://", "https://")):
                continue
            result = anchor.find_parent(class_="result")
            snippet = ""
            if result:
                snippet_el = result.select_one(".result__snippet")
                snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
            results.append(
                self._result_from_live_item(len(results) + 1, href, anchor.get_text(" ", strip=True), snippet, query, competitor, source_type)
            )
            if len(results) >= max_results:
                break
        return results

    def _result_from_fixture(self, rank: int, item: dict, query: str, competitor: str) -> dict:
        return {
            "url": item["url"],
            "title": item["title"],
            "snippet": item["content"][:220],
            "source_type": item["source_type"],
            "rank": rank,
            "query": query,
            "competitor": competitor,
            "retrieved_at": iso_now(),
        }

    def _result_from_live_item(
        self,
        rank: int,
        url: str,
        title: str,
        snippet: str,
        query: str,
        competitor: str,
        requested_source_type: str,
    ) -> dict:
        source_type = requested_source_type if requested_source_type != "mixed" else infer_source_type(url, title, query)
        return {
            "url": url,
            "title": title or url,
            "snippet": snippet or "",
            "source_type": normalize_source_type(source_type),
            "rank": rank,
            "query": query,
            "competitor": competitor,
            "retrieved_at": iso_now(),
        }


def normalize_duckduckgo_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(target)
    return url


def infer_source_type(url: str, title: str, query: str) -> str:
    text = f"{url} {title} {query}".lower()
    if "pricing" in text or "price" in text or "价格" in text:
        return "pricing"
    if "docs" in text or "documentation" in text or "api" in text:
        return "docs"
    if "github.com" in text:
        return "github"
    if "g2.com" in text or "capterra" in text or "review" in text or "reviews" in text or "评论" in text:
        return "review"
    if "news" in text or "blog" in text or "changelog" in text or "更新" in text:
        return "news"
    return "official"


def normalize_source_type(value: object) -> str:
    normalized = str(value or "mixed").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "official_spec": "official",
        "official_specs": "official",
        "official_page": "official",
        "official_product": "official",
        "official_spec_pricing": "official",
        "official_specs_pricing": "official",
        "official_price": "pricing",
        "product_page": "official",
        "price": "pricing",
        "pricing_channel": "pricing",
        "channel_pricing": "pricing",
        "current_pricing_channel": "pricing",
        "latest_pricing_channel": "pricing",
        "commerce": "pricing",
        "ecommerce": "pricing",
        "third_party_review": "review",
        "third_party_reviews": "review",
        "user_review": "review",
        "user_reviews": "review",
        "market_news": "news",
        "media_news": "news",
        "forum": "review",
        "community": "review",
        "social": "review",
        "ecosystem_experience": "review",
    }
    if normalized in aliases:
        return aliases[normalized]
    if "pricing" in normalized or "price" in normalized or "channel" in normalized:
        return "pricing"
    if "official" in normalized or "spec" in normalized or "product" in normalized:
        return "official"
    if "review" in normalized or "feedback" in normalized or "experience" in normalized or "forum" in normalized:
        return "review"
    if "news" in normalized or "market" in normalized:
        return "news"
    return normalized or "mixed"
