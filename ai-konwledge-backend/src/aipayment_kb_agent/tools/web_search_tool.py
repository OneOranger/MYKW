from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class WebSearchTool:
    def __init__(self, timeout_s: float = 8.0):
        self.timeout_s = timeout_s

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "no_redirect": 1,
            "skip_disambig": 1,
        }
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except Exception:
            logger.exception("web_search:request_failed query=%s", query)
            return []

        results: list[dict] = []
        abstract = payload.get("AbstractText") or ""
        if abstract:
            results.append(
                {
                    "title": payload.get("Heading") or query,
                    "url": payload.get("AbstractURL") or "",
                    "snippet": abstract,
                }
            )
        for item in payload.get("RelatedTopics", []):
            if isinstance(item, dict) and item.get("Text"):
                results.append(
                    {
                        "title": item.get("Text", "")[:80],
                        "url": item.get("FirstURL", ""),
                        "snippet": item.get("Text", ""),
                    }
                )
            if len(results) >= max_results:
                break
        logger.info("web_search:done query=%s results=%s", query, len(results))
        return results[:max_results]
