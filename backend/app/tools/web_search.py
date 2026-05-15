from __future__ import annotations

from app.config import get_settings
from app.core.time import iso_now
from app.tools.base import BaseTool
from app.tools.fixtures import fixture_results_for


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search public web sources. Offline mode uses deterministic public-source fixtures."

    async def call(self, input_data: dict) -> dict:
        settings = get_settings()
        query = input_data.get("query", "")
        competitor = input_data.get("competitor") or query
        max_results = int(input_data.get("max_results") or settings.max_search_results_per_competitor)

        if settings.offline_mode:
            fixtures = fixture_results_for(competitor)
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
            if not results:
                results = [
                    {
                        "url": f"offline://generic/{competitor.replace(' ', '-').lower()}",
                        "title": f"{competitor} public information fixture",
                        "snippet": "No seeded fixture matched this competitor; downstream agents must mark unsupported conclusions as unknown.",
                        "source_type": "unknown",
                        "rank": 1,
                        "query": query,
                        "competitor": competitor,
                        "retrieved_at": iso_now(),
                    }
                ]
            return {"search_results": results, "provider": "offline_fixture"}

        # Search engine crawling is intentionally not emulated. Production should
        # configure a compliant SERP API here instead of scraping result pages.
        return {
            "search_results": [],
            "provider": "not_configured",
            "warning": "No compliant search API configured. Set COMPETESCOPE_OFFLINE_MODE=true for fixtures or add a provider.",
        }

