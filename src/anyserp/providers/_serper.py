from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from .._errors import AnySerpError

SERPER_API_BASE = "https://google.serper.dev"

TYPE_ENDPOINTS: dict[str, str] = {
    "web": "/search",
    "images": "/images",
    "news": "/news",
    "videos": "/videos",
}

DATE_MAP: dict[str, str] = {
    "day": "qdr:d",
    "week": "qdr:w",
    "month": "qdr:m",
    "year": "qdr:y",
}


class _SerperAdapter:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "serper"

    def supports_type(self, search_type: str) -> bool:
        return True

    async def _make_request(self, endpoint: str, body: dict[str, Any]) -> Any:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{SERPER_API_BASE}{endpoint}",
                headers={"Content-Type": "application/json", "X-API-KEY": self._api_key},
                json=body,
            )

        if res.status_code >= 400:
            try:
                error_body = res.json()
            except Exception:
                error_body = {"message": res.reason_phrase}
            raise AnySerpError(
                res.status_code,
                error_body.get("message", res.reason_phrase or "Unknown error"),
                {"provider_name": "serper", "raw": error_body},
            )
        return res.json()

    async def search(self, request: dict[str, Any]) -> dict[str, Any]:
        search_type = request.get("type", "web")
        endpoint = TYPE_ENDPOINTS[search_type]

        body: dict[str, Any] = {"q": request["query"]}
        if request.get("num"):
            body["num"] = request["num"]
        if request.get("page") and request["page"] > 1:
            body["page"] = request["page"]
        if request.get("country"):
            body["gl"] = request["country"]
        if request.get("language"):
            body["hl"] = request["language"]
        if request.get("dateRange"):
            body["tbs"] = DATE_MAP.get(request["dateRange"])

        data = await self._make_request(endpoint, body)

        results: list[dict[str, Any]] = []

        if search_type == "web":
            for i, r in enumerate(data.get("organic", [])):
                results.append({
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet", ""),
                    **({"domain": r["domain"]} if r.get("domain") else {}),
                    **({"datePublished": r["date"]} if r.get("date") else {}),
                })
        elif search_type == "images":
            for i, r in enumerate(data.get("images", [])):
                results.append({
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet", ""),
                    **({"imageUrl": r["imageUrl"]} if r.get("imageUrl") else {}),
                    **({"imageWidth": r["imageWidth"]} if r.get("imageWidth") else {}),
                    **({"imageHeight": r["imageHeight"]} if r.get("imageHeight") else {}),
                    **({"domain": r["domain"]} if r.get("domain") else {}),
                    **({"thumbnail": r["thumbnailUrl"]} if r.get("thumbnailUrl") else {}),
                })
        elif search_type == "news":
            for i, r in enumerate(data.get("news", [])):
                results.append({
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet", ""),
                    **({"source": r["source"]} if r.get("source") else {}),
                    **({"datePublished": r["date"]} if r.get("date") else {}),
                    **({"thumbnail": r["imageUrl"]} if r.get("imageUrl") else {}),
                })
        elif search_type == "videos":
            for i, r in enumerate(data.get("videos", [])):
                results.append({
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet", ""),
                    **({"duration": r["duration"]} if r.get("duration") else {}),
                    **({"channel": r["channel"]} if r.get("channel") else {}),
                    **({"thumbnail": r["imageUrl"]} if r.get("imageUrl") else {}),
                    **({"datePublished": r["date"]} if r.get("date") else {}),
                })

        response: dict[str, Any] = {
            "provider": "serper",
            "query": request["query"],
            "results": results,
        }

        sp = data.get("searchParameters", {})
        if sp.get("timeTaken"):
            response["searchTime"] = sp["timeTaken"] * 1000

        related = data.get("relatedSearches")
        if related:
            response["relatedSearches"] = [r.get("query", "") for r in related]

        paa = data.get("peopleAlsoAsk")
        if paa:
            response["peopleAlsoAsk"] = [
                {
                    "question": p.get("question", ""),
                    **({"snippet": p["snippet"]} if p.get("snippet") else {}),
                    **({"title": p["title"]} if p.get("title") else {}),
                    **({"url": p["link"]} if p.get("link") else {}),
                }
                for p in paa
            ]

        kg = data.get("knowledgeGraph")
        if kg:
            panel: dict[str, Any] = {"title": kg.get("title", "")}
            if kg.get("type"):
                panel["type"] = kg["type"]
            if kg.get("description"):
                panel["description"] = kg["description"]
            if kg.get("descriptionSource"):
                panel["source"] = kg["descriptionSource"]
            if kg.get("descriptionLink"):
                panel["sourceUrl"] = kg["descriptionLink"]
            if kg.get("imageUrl"):
                panel["imageUrl"] = kg["imageUrl"]
            if kg.get("attributes"):
                panel["attributes"] = kg["attributes"]
            response["knowledgePanel"] = panel

        ab = data.get("answerBox")
        if ab:
            response["answerBox"] = {
                "snippet": ab.get("snippet") or ab.get("answer", ""),
                **({"title": ab["title"]} if ab.get("title") else {}),
                **({"url": ab["link"]} if ab.get("link") else {}),
            }

        return response


def create_serper_adapter(api_key: str) -> _SerperAdapter:
    return _SerperAdapter(api_key)
