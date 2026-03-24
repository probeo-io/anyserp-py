from __future__ import annotations

from typing import Any

import httpx

from .._errors import AnySerpError

SCRAPINGDOG_BASE = "https://api.scrapingdog.com"

ENDPOINT_MAP: dict[str, str] = {
    "web": "/google",
    "images": "/google_images",
    "news": "/google_news",
    "videos": "/google",
}


class _ScrapingDogAdapter:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "scrapingdog"

    def supports_type(self, search_type: str) -> bool:
        return search_type in ("web", "images", "news")

    async def _make_request(self, endpoint: str, params: dict[str, str]) -> Any:
        params["api_key"] = self._api_key
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{SCRAPINGDOG_BASE}{endpoint}",
                params=params,
                headers={"Accept": "application/json"},
            )

        if res.status_code >= 400:
            try:
                error_body = res.json()
            except Exception:
                error_body = {"message": res.reason_phrase}
            raise AnySerpError(
                res.status_code,
                error_body.get("error", res.reason_phrase or "Unknown error"),
                {"provider_name": "scrapingdog", "raw": error_body},
            )
        return res.json()

    async def search(self, request: dict[str, Any]) -> dict[str, Any]:
        search_type = request.get("type", "web")
        endpoint = ENDPOINT_MAP[search_type]
        params: dict[str, str] = {"query": request["query"]}

        if request.get("num"):
            params["results"] = str(request["num"])
        if request.get("page") and request["page"] > 1:
            params["page"] = str(request["page"] - 1)  # 0-indexed
        if request.get("country"):
            params["country"] = request["country"]
        if request.get("language"):
            params["language"] = request["language"]

        data = await self._make_request(endpoint, params)

        results: list[dict[str, Any]] = []

        if search_type == "web":
            organic = data if isinstance(data, list) else (data.get("organic_results") or data.get("organic_data") or [])
            for i, r in enumerate(organic):
                result: dict[str, Any] = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link") or r.get("url", ""),
                    "description": r.get("snippet") or r.get("description", ""),
                }
                if r.get("displayed_link") or r.get("domain"):
                    result["domain"] = r.get("displayed_link") or r.get("domain")
                if r.get("date"):
                    result["datePublished"] = r["date"]
                results.append(result)
        elif search_type == "images":
            images = data if isinstance(data, list) else (data.get("image_results") or [])
            for i, r in enumerate(images):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link") or r.get("url", ""),
                    "description": r.get("title", ""),
                }
                if r.get("original") or r.get("image"):
                    result["imageUrl"] = r.get("original") or r.get("image")
                if r.get("original_width"):
                    result["imageWidth"] = r["original_width"]
                if r.get("original_height"):
                    result["imageHeight"] = r["original_height"]
                if r.get("thumbnail"):
                    result["thumbnail"] = r["thumbnail"]
                if r.get("source"):
                    result["source"] = r["source"]
                results.append(result)
        elif search_type == "news":
            news = data if isinstance(data, list) else (data.get("news_results") or [])
            for i, r in enumerate(news):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link") or r.get("url", ""),
                    "description": r.get("snippet") or r.get("description", ""),
                }
                if r.get("source"):
                    result["source"] = r["source"]
                if r.get("date"):
                    result["datePublished"] = r["date"]
                if r.get("thumbnail") or r.get("image"):
                    result["thumbnail"] = r.get("thumbnail") or r.get("image")
                results.append(result)

        response: dict[str, Any] = {
            "provider": "scrapingdog",
            "query": request["query"],
            "results": results,
        }

        if isinstance(data, dict) and data.get("people_also_ask"):
            response["peopleAlsoAsk"] = [
                {
                    "question": q.get("question", ""),
                    **({"snippet": q["snippet"]} if q.get("snippet") else {}),
                    **({"title": q["title"]} if q.get("title") else {}),
                    **({"url": q["link"]} if q.get("link") else {}),
                }
                for q in data["people_also_ask"]
            ]

        return response


def create_scrapingdog_adapter(api_key: str) -> _ScrapingDogAdapter:
    return _ScrapingDogAdapter(api_key)
