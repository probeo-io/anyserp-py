from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from .._errors import AnySerpError

BING_API_BASE = "https://api.bing.microsoft.com/v7.0"

TYPE_ENDPOINTS: dict[str, str] = {
    "web": "/search",
    "images": "/images/search",
    "news": "/news/search",
    "videos": "/videos/search",
}

FRESHNESS_MAP: dict[str, str] = {
    "day": "Day",
    "week": "Week",
    "month": "Month",
}


class _BingAdapter:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "bing"

    def supports_type(self, search_type: str) -> bool:
        return True

    async def _make_request(self, endpoint: str, params: dict[str, str]) -> Any:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BING_API_BASE}{endpoint}",
                params=params,
                headers={"Ocp-Apim-Subscription-Key": self._api_key},
            )

        if res.status_code >= 400:
            try:
                error_body = res.json()
            except Exception:
                error_body = {"message": res.reason_phrase}
            msg = (error_body.get("error", {}) or {}).get("message", res.reason_phrase or "Unknown error")
            raise AnySerpError(res.status_code, msg, {"provider_name": "bing", "raw": error_body})
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
            params["cc"] = request["country"]
        if request.get("language"):
            params["setLang"] = request["language"]
        if request.get("safe"):
            params["safeSearch"] = "Strict"
        if request.get("dateRange") and request["dateRange"] in FRESHNESS_MAP:
            params["freshness"] = FRESHNESS_MAP[request["dateRange"]]

        data = await self._make_request(endpoint, params)

        results: list[dict[str, Any]] = []

        if search_type == "web":
            for i, r in enumerate((data.get("webPages", {}) or {}).get("value", [])):
                result: dict[str, Any] = {
                    "position": i + 1,
                    "title": r.get("name", ""),
                    "url": r.get("url", ""),
                    "description": r.get("snippet", ""),
                }
                if r.get("displayUrl") and r.get("url"):
                    try:
                        result["domain"] = urlparse(r["url"]).hostname
                    except Exception:
                        pass
                if r.get("dateLastCrawled"):
                    result["datePublished"] = r["dateLastCrawled"]
                results.append(result)
        elif search_type == "images":
            for i, r in enumerate(data.get("value", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("name", ""),
                    "url": r.get("hostPageUrl", ""),
                    "description": r.get("name", ""),
                }
                if r.get("contentUrl"):
                    result["imageUrl"] = r["contentUrl"]
                if r.get("width"):
                    result["imageWidth"] = r["width"]
                if r.get("height"):
                    result["imageHeight"] = r["height"]
                if r.get("thumbnailUrl"):
                    result["thumbnail"] = r["thumbnailUrl"]
                if r.get("hostPageDisplayUrl") and r.get("hostPageUrl"):
                    try:
                        result["domain"] = urlparse(r["hostPageUrl"]).hostname
                    except Exception:
                        pass
                results.append(result)
        elif search_type == "news":
            for i, r in enumerate(data.get("value", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("name", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                }
                providers = r.get("provider", [])
                if providers and providers[0].get("name"):
                    result["source"] = providers[0]["name"]
                if r.get("datePublished"):
                    result["datePublished"] = r["datePublished"]
                img = r.get("image", {})
                if img:
                    thumb = (img.get("thumbnail") or {}).get("contentUrl")
                    if thumb:
                        result["thumbnail"] = thumb
                results.append(result)
        elif search_type == "videos":
            for i, r in enumerate(data.get("value", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("name", ""),
                    "url": r.get("contentUrl") or r.get("hostPageUrl", ""),
                    "description": r.get("description", ""),
                }
                if r.get("duration"):
                    result["duration"] = r["duration"]
                creator = r.get("creator", {})
                if isinstance(creator, dict) and creator.get("name"):
                    result["channel"] = creator["name"]
                if r.get("thumbnailUrl"):
                    result["thumbnail"] = r["thumbnailUrl"]
                if r.get("datePublished"):
                    result["datePublished"] = r["datePublished"]
                results.append(result)

        response: dict[str, Any] = {
            "provider": "bing",
            "query": request["query"],
            "results": results,
        }

        total = (data.get("webPages", {}) or {}).get("totalEstimatedMatches") or data.get("totalEstimatedMatches")
        if total:
            response["totalResults"] = total

        return response


def create_bing_adapter(api_key: str) -> _BingAdapter:
    return _BingAdapter(api_key)
