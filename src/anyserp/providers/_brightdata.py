from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from .._errors import AnySerpError

BRIGHTDATA_API_BASE = "https://api.brightdata.com/request"

TBM_MAP: dict[str, str | None] = {
    "web": None,
    "images": "isch",
    "news": "nws",
    "videos": "vid",
}


class _BrightDataAdapter:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "brightdata"

    def supports_type(self, search_type: str) -> bool:
        return True

    async def _make_request(self, search_url: str) -> Any:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                BRIGHTDATA_API_BASE,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
                json={
                    "zone": "serp",
                    "url": search_url,
                    "format": "raw",
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
                {"provider_name": "brightdata", "raw": error_body},
            )
        return res.json()

    @staticmethod
    def _build_search_url(request: dict[str, Any], search_type: str) -> str:
        params: dict[str, str] = {"q": request["query"]}

        tbm = TBM_MAP.get(search_type)
        if tbm:
            params["tbm"] = tbm

        if request.get("country"):
            params["gl"] = request["country"]
        if request.get("language"):
            params["hl"] = request["language"]
        if request.get("num"):
            params["num"] = str(request["num"])
        if request.get("page") and request["page"] > 1:
            params["start"] = str((request["page"] - 1) * (request.get("num") or 10))
        if request.get("safe"):
            params["safe"] = "active"

        params["brd_json"] = "1"
        return f"https://www.google.com/search?{urlencode(params)}"

    async def search(self, request: dict[str, Any]) -> dict[str, Any]:
        search_type = request.get("type", "web")
        search_url = self._build_search_url(request, search_type)
        data = await self._make_request(search_url)

        results: list[dict[str, Any]] = []

        if search_type == "web":
            for i, r in enumerate(data.get("organic", [])):
                result: dict[str, Any] = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("description", ""),
                }
                if r.get("display_link"):
                    result["domain"] = r["display_link"]
                results.append(result)
        elif search_type == "images":
            for i, r in enumerate(data.get("organic") or data.get("images", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("description") or r.get("title", ""),
                }
                if r.get("original") or r.get("link"):
                    result["imageUrl"] = r.get("original") or r.get("link")
                if r.get("thumbnail"):
                    result["thumbnail"] = r["thumbnail"]
                if r.get("display_link"):
                    result["source"] = r["display_link"]
                results.append(result)
        elif search_type == "news":
            for i, r in enumerate(data.get("organic") or data.get("news", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("description", ""),
                }
                if r.get("display_link"):
                    result["source"] = r["display_link"]
                if r.get("date"):
                    result["datePublished"] = r["date"]
                results.append(result)
        elif search_type == "videos":
            for i, r in enumerate(data.get("organic") or data.get("videos", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("description", ""),
                }
                if r.get("thumbnail"):
                    result["thumbnail"] = r["thumbnail"]
                if r.get("duration"):
                    result["duration"] = r["duration"]
                results.append(result)

        response: dict[str, Any] = {
            "provider": "brightdata",
            "query": request["query"],
            "results": results,
        }

        kp = data.get("knowledge_panel")
        if kp:
            panel: dict[str, Any] = {"title": kp.get("title", "")}
            if kp.get("type"):
                panel["type"] = kp["type"]
            if kp.get("description"):
                panel["description"] = kp["description"]
            if kp.get("image"):
                panel["imageUrl"] = kp["image"]
            response["knowledgePanel"] = panel

        paa = data.get("people_also_ask")
        if paa:
            response["peopleAlsoAsk"] = [
                {
                    "question": q.get("question", ""),
                    **({"snippet": q["snippet"]} if q.get("snippet") else {}),
                    **({"title": q["title"]} if q.get("title") else {}),
                    **({"url": q.get("link") or q.get("url")} if q.get("link") or q.get("url") else {}),
                }
                for q in paa
            ]

        rs = data.get("related_searches")
        if rs:
            response["relatedSearches"] = [
                r if isinstance(r, str) else (r.get("query") or r.get("title", ""))
                for r in rs
            ]

        return response


def create_brightdata_adapter(api_key: str) -> _BrightDataAdapter:
    return _BrightDataAdapter(api_key)
