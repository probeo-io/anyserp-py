from __future__ import annotations

from typing import Any

import httpx

from .._errors import AnySerpError

GOOGLE_CSE_BASE = "https://www.googleapis.com/customsearch/v1"

TYPE_MAP: dict[str, str | None] = {
    "web": None,
    "images": "image",
    "news": None,
    "videos": None,
}

DATE_MAP: dict[str, str] = {
    "day": "d1",
    "week": "w1",
    "month": "m1",
    "year": "y1",
}


class _GoogleAdapter:
    def __init__(self, api_key: str, engine_id: str) -> None:
        self._api_key = api_key
        self._engine_id = engine_id

    @property
    def name(self) -> str:
        return "google"

    def supports_type(self, search_type: str) -> bool:
        return search_type in ("web", "images")

    async def _make_request(self, params: dict[str, str]) -> Any:
        params["key"] = self._api_key
        params["cx"] = self._engine_id
        async with httpx.AsyncClient() as client:
            res = await client.get(GOOGLE_CSE_BASE, params=params)

        if res.status_code >= 400:
            try:
                error_body = res.json()
            except Exception:
                error_body = {"message": res.reason_phrase}
            msg = (error_body.get("error", {}) or {}).get("message", res.reason_phrase or "Unknown error")
            raise AnySerpError(res.status_code, msg, {"provider_name": "google", "raw": error_body})
        return res.json()

    async def search(self, request: dict[str, Any]) -> dict[str, Any]:
        search_type = request.get("type", "web")
        params: dict[str, str] = {"q": request["query"]}

        if request.get("num"):
            params["num"] = str(min(request["num"], 10))
        if request.get("page") and request["page"] > 1:
            params["start"] = str(((request["page"] - 1) * (request.get("num") or 10)) + 1)
        if request.get("country"):
            params["gl"] = request["country"]
        if request.get("language"):
            params["lr"] = f"lang_{request['language']}"
        if request.get("safe"):
            params["safe"] = "active"
        if request.get("dateRange"):
            params["dateRestrict"] = DATE_MAP.get(request["dateRange"], "")

        cse_type = TYPE_MAP.get(search_type)
        if cse_type:
            params["searchType"] = cse_type

        data = await self._make_request(params)

        results: list[dict[str, Any]] = []
        for i, item in enumerate(data.get("items", [])):
            result: dict[str, Any] = {
                "position": i + 1,
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "description": item.get("snippet", ""),
            }
            if item.get("displayLink"):
                result["domain"] = item["displayLink"]

            if search_type == "images" and item.get("image"):
                result["imageUrl"] = item["link"]
                if item["image"].get("width"):
                    result["imageWidth"] = item["image"]["width"]
                if item["image"].get("height"):
                    result["imageHeight"] = item["image"]["height"]
                if item["image"].get("thumbnailLink"):
                    result["thumbnail"] = item["image"]["thumbnailLink"]

            metatags = (item.get("pagemap", {}) or {}).get("metatags", [])
            if metatags and metatags[0].get("article:published_time"):
                result["datePublished"] = metatags[0]["article:published_time"]

            results.append(result)

        response: dict[str, Any] = {
            "provider": "google",
            "query": request["query"],
            "results": results,
        }

        si = data.get("searchInformation", {})
        if si.get("totalResults"):
            response["totalResults"] = int(si["totalResults"])
        if si.get("searchTime"):
            response["searchTime"] = si["searchTime"] * 1000

        return response


def create_google_adapter(api_key: str, engine_id: str) -> _GoogleAdapter:
    return _GoogleAdapter(api_key, engine_id)
