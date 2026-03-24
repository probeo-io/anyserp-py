from __future__ import annotations

from typing import Any

import httpx

from .._errors import AnySerpError

BRAVE_API_BASE = "https://api.search.brave.com/res/v1"

TYPE_ENDPOINTS: dict[str, str] = {
    "web": "/web/search",
    "images": "/images/search",
    "news": "/news/search",
    "videos": "/videos/search",
}

FRESHNESS_MAP: dict[str, str] = {
    "day": "pd",
    "week": "pw",
    "month": "pm",
    "year": "py",
}


class _BraveAdapter:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "brave"

    def supports_type(self, search_type: str) -> bool:
        return True

    async def _make_request(self, endpoint: str, params: dict[str, str]) -> Any:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BRAVE_API_BASE}{endpoint}",
                params=params,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": self._api_key,
                },
            )

        if res.status_code >= 400:
            try:
                error_body = res.json()
            except Exception:
                error_body = {"message": res.reason_phrase}
            raise AnySerpError(
                res.status_code,
                error_body.get("message", res.reason_phrase or "Unknown error"),
                {"provider_name": "brave", "raw": error_body},
            )
        return res.json()

    async def search(self, request: dict[str, Any]) -> dict[str, Any]:
        search_type = request.get("type", "web")
        endpoint = TYPE_ENDPOINTS[search_type]
        params: dict[str, str] = {"q": request["query"]}

        if request.get("num"):
            params["count"] = str(request["num"])
        if request.get("page") and request["page"] > 1:
            params["offset"] = str((request["page"] - 1) * (request.get("num") or 10))
        if request.get("country"):
            params["country"] = request["country"]
        if request.get("language"):
            params["search_lang"] = request["language"]
        if request.get("safe"):
            params["safesearch"] = "strict"
        if request.get("dateRange"):
            params["freshness"] = FRESHNESS_MAP.get(request["dateRange"], "")

        data = await self._make_request(endpoint, params)

        results: list[dict[str, Any]] = []

        if search_type == "web":
            for i, r in enumerate((data.get("web", {}) or {}).get("results", [])):
                result: dict[str, Any] = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                }
                meta_url = r.get("meta_url")
                if isinstance(meta_url, dict) and meta_url.get("hostname"):
                    result["domain"] = meta_url["hostname"]
                if r.get("page_age"):
                    result["datePublished"] = r["page_age"]
                thumb = r.get("thumbnail")
                if isinstance(thumb, dict) and thumb.get("src"):
                    result["thumbnail"] = thumb["src"]
                results.append(result)
        elif search_type == "images":
            for i, r in enumerate(data.get("results", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description") or r.get("title", ""),
                }
                props = r.get("properties", {})
                if isinstance(props, dict):
                    if props.get("url"):
                        result["imageUrl"] = props["url"]
                    if props.get("width"):
                        result["imageWidth"] = props["width"]
                    if props.get("height"):
                        result["imageHeight"] = props["height"]
                thumb = r.get("thumbnail")
                if isinstance(thumb, dict) and thumb.get("src"):
                    result["thumbnail"] = thumb["src"]
                if r.get("source"):
                    result["source"] = r["source"]
                results.append(result)
        elif search_type == "news":
            for i, r in enumerate(data.get("results", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                }
                meta_url = r.get("meta_url")
                if isinstance(meta_url, dict) and meta_url.get("hostname"):
                    result["source"] = meta_url["hostname"]
                if r.get("age"):
                    result["datePublished"] = r["age"]
                thumb = r.get("thumbnail")
                if isinstance(thumb, dict) and thumb.get("src"):
                    result["thumbnail"] = thumb["src"]
                results.append(result)
        elif search_type == "videos":
            for i, r in enumerate(data.get("results", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                }
                thumb = r.get("thumbnail")
                if isinstance(thumb, dict) and thumb.get("src"):
                    result["thumbnail"] = thumb["src"]
                if r.get("age"):
                    result["datePublished"] = r["age"]
                results.append(result)

        response: dict[str, Any] = {
            "provider": "brave",
            "query": request["query"],
            "results": results,
        }

        if search_type == "web":
            query_data = data.get("query", {})
            if isinstance(query_data, dict) and query_data.get("related_searches"):
                response["relatedSearches"] = [
                    r.get("query", r) if isinstance(r, dict) else r
                    for r in query_data["related_searches"]
                ]

        return response


def create_brave_adapter(api_key: str) -> _BraveAdapter:
    return _BraveAdapter(api_key)
