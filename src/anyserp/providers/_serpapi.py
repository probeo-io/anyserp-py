from __future__ import annotations

from typing import Any

import httpx

from .._errors import AnySerpError

SERPAPI_BASE = "https://serpapi.com/search.json"

ENGINE_MAP: dict[str, str] = {
    "web": "google",
    "images": "google_images",
    "news": "google_news",
    "videos": "google_videos",
}

DATE_MAP: dict[str, str] = {
    "day": "qdr:d",
    "week": "qdr:w",
    "month": "qdr:m",
    "year": "qdr:y",
}


class _SerpApiAdapter:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "serpapi"

    def supports_type(self, search_type: str) -> bool:
        return True

    async def _make_request(self, params: dict[str, str]) -> Any:
        params["api_key"] = self._api_key
        params["output"] = "json"
        async with httpx.AsyncClient() as client:
            res = await client.get(SERPAPI_BASE, params=params)

        if res.status_code >= 400:
            try:
                error_body = res.json()
            except Exception:
                error_body = {"message": res.reason_phrase}
            raise AnySerpError(
                res.status_code,
                error_body.get("error", res.reason_phrase or "Unknown error"),
                {"provider_name": "serpapi", "raw": error_body},
            )
        return res.json()

    async def search(self, request: dict[str, Any]) -> dict[str, Any]:
        search_type = request.get("type", "web")
        params: dict[str, str] = {
            "engine": ENGINE_MAP[search_type],
            "q": request["query"],
        }

        if request.get("num"):
            params["num"] = str(request["num"])
        if request.get("page") and request["page"] > 1:
            params["start"] = str((request["page"] - 1) * (request.get("num") or 10))
        if request.get("country"):
            params["gl"] = request["country"]
        if request.get("language"):
            params["hl"] = request["language"]
        if request.get("safe"):
            params["safe"] = "active"
        if request.get("dateRange"):
            params["tbs"] = DATE_MAP.get(request["dateRange"], "")

        data = await self._make_request(params)

        results: list[dict[str, Any]] = []

        if search_type == "web":
            for i, r in enumerate(data.get("organic_results", [])):
                results.append({
                    "position": r.get("position", i + 1),
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet", ""),
                    **({"domain": r["displayed_link"]} if r.get("displayed_link") else {}),
                    **({"datePublished": r["date"]} if r.get("date") else {}),
                    **({"thumbnail": r["thumbnail"]} if r.get("thumbnail") else {}),
                })
        elif search_type == "images":
            for i, r in enumerate(data.get("images_results", [])):
                results.append({
                    "position": r.get("position", i + 1),
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet", ""),
                    **({"imageUrl": r["original"]} if r.get("original") else {}),
                    **({"imageWidth": r["original_width"]} if r.get("original_width") else {}),
                    **({"imageHeight": r["original_height"]} if r.get("original_height") else {}),
                    **({"thumbnail": r["thumbnail"]} if r.get("thumbnail") else {}),
                    **({"source": r["source"]} if r.get("source") else {}),
                })
        elif search_type == "news":
            for i, r in enumerate(data.get("news_results", [])):
                source = r.get("source")
                if isinstance(source, dict):
                    source = source.get("name")
                results.append({
                    "position": r.get("position", i + 1),
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet", ""),
                    **({"source": source} if source else {}),
                    **({"datePublished": r["date"]} if r.get("date") else {}),
                    **({"thumbnail": r["thumbnail"]} if r.get("thumbnail") else {}),
                })
        elif search_type == "videos":
            for i, r in enumerate(data.get("video_results", [])):
                channel = r.get("channel")
                if isinstance(channel, dict):
                    channel = channel.get("name")
                thumbnail = r.get("thumbnail")
                if isinstance(thumbnail, dict):
                    thumbnail = thumbnail.get("static")
                results.append({
                    "position": r.get("position", i + 1),
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet", ""),
                    **({"duration": r["duration"]} if r.get("duration") else {}),
                    **({"channel": channel} if channel else {}),
                    **({"thumbnail": thumbnail} if thumbnail else {}),
                    **({"datePublished": r["date"]} if r.get("date") else {}),
                })

        response: dict[str, Any] = {
            "provider": "serpapi",
            "query": request["query"],
            "results": results,
        }

        si = data.get("search_information", {})
        if si.get("total_results"):
            response["totalResults"] = si["total_results"]
        if si.get("time_taken_displayed"):
            response["searchTime"] = float(si["time_taken_displayed"]) * 1000

        related = data.get("related_searches")
        if related:
            response["relatedSearches"] = [r.get("query", "") for r in related]

        rq = data.get("related_questions")
        if rq:
            response["peopleAlsoAsk"] = [
                {
                    "question": q.get("question", ""),
                    **({"snippet": q["snippet"]} if q.get("snippet") else {}),
                    **({"title": q["title"]} if q.get("title") else {}),
                    **({"url": q["link"]} if q.get("link") else {}),
                }
                for q in rq
            ]

        kg = data.get("knowledge_graph")
        if kg:
            panel: dict[str, Any] = {"title": kg.get("title", "")}
            if kg.get("type"):
                panel["type"] = kg["type"]
            if kg.get("description"):
                panel["description"] = kg["description"]
            source = kg.get("source")
            if isinstance(source, dict):
                if source.get("name"):
                    panel["source"] = source["name"]
                if source.get("link"):
                    panel["sourceUrl"] = source["link"]
            header_images = kg.get("header_images")
            if header_images and len(header_images) > 0:
                img = header_images[0].get("image")
                if img:
                    panel["imageUrl"] = img
            response["knowledgePanel"] = panel

        ab = data.get("answer_box")
        if ab:
            response["answerBox"] = {
                "snippet": ab.get("snippet") or ab.get("answer", ""),
                **({"title": ab["title"]} if ab.get("title") else {}),
                **({"url": ab["link"]} if ab.get("link") else {}),
            }

        return response


def create_serpapi_adapter(api_key: str) -> _SerpApiAdapter:
    return _SerpApiAdapter(api_key)
