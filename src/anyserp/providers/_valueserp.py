from __future__ import annotations

from typing import Any

import httpx

from .._errors import AnySerpError

VALUESERP_BASE = "https://api.valueserp.com/search"

SEARCH_TYPE_MAP: dict[str, str] = {
    "web": "web",
    "images": "images",
    "news": "news",
    "videos": "videos",
}

TIME_PERIOD_MAP: dict[str, str] = {
    "day": "last_day",
    "week": "last_week",
    "month": "last_month",
    "year": "last_year",
}


class _ValueSerpAdapter:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "valueserp"

    def supports_type(self, search_type: str) -> bool:
        return True

    async def _make_request(self, params: dict[str, str]) -> Any:
        params["api_key"] = self._api_key
        params["output"] = "json"
        async with httpx.AsyncClient() as client:
            res = await client.get(
                VALUESERP_BASE,
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
                {"provider_name": "valueserp", "raw": error_body},
            )
        return res.json()

    async def search(self, request: dict[str, Any]) -> dict[str, Any]:
        search_type = request.get("type", "web")
        params: dict[str, str] = {
            "q": request["query"],
            "search_type": SEARCH_TYPE_MAP[search_type],
        }

        if request.get("num"):
            params["num"] = str(request["num"])
        if request.get("page") and request["page"] > 1:
            params["page"] = str(request["page"])
        if request.get("country"):
            params["gl"] = request["country"]
        if request.get("language"):
            params["hl"] = request["language"]
        if request.get("safe"):
            params["safe"] = "active"
        if request.get("dateRange"):
            params["time_period"] = TIME_PERIOD_MAP.get(request["dateRange"], "")

        data = await self._make_request(params)

        results: list[dict[str, Any]] = []

        if search_type == "web":
            for i, r in enumerate(data.get("organic_results", [])):
                result: dict[str, Any] = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet", ""),
                }
                if r.get("domain"):
                    result["domain"] = r["domain"]
                if r.get("date"):
                    result["datePublished"] = r["date"]
                results.append(result)
        elif search_type == "images":
            for i, r in enumerate(data.get("image_results", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
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
            for i, r in enumerate(data.get("news_results", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet", ""),
                }
                if r.get("source"):
                    result["source"] = r["source"]
                if r.get("date"):
                    result["datePublished"] = r["date"]
                if r.get("thumbnail"):
                    result["thumbnail"] = r["thumbnail"]
                results.append(result)
        elif search_type == "videos":
            for i, r in enumerate(data.get("video_results", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet") or r.get("description", ""),
                }
                if r.get("duration"):
                    result["duration"] = r["duration"]
                if r.get("channel"):
                    result["channel"] = r["channel"]
                if r.get("thumbnail"):
                    result["thumbnail"] = r["thumbnail"]
                if r.get("date"):
                    result["datePublished"] = r["date"]
                results.append(result)

        response: dict[str, Any] = {
            "provider": "valueserp",
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

        paa = data.get("people_also_ask")
        if paa:
            response["peopleAlsoAsk"] = [
                {
                    "question": q.get("question", ""),
                    **({"snippet": q["snippet"]} if q.get("snippet") else {}),
                    **({"title": q["title"]} if q.get("title") else {}),
                    **({"url": q["link"]} if q.get("link") else {}),
                }
                for q in paa
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
            if kg.get("image"):
                panel["imageUrl"] = kg["image"]
            response["knowledgePanel"] = panel

        ab = data.get("answer_box")
        if ab:
            response["answerBox"] = {
                "snippet": ab.get("snippet") or ab.get("answer", ""),
                **({"title": ab["title"]} if ab.get("title") else {}),
                **({"url": ab["link"]} if ab.get("link") else {}),
            }

        return response


def create_valueserp_adapter(api_key: str) -> _ValueSerpAdapter:
    return _ValueSerpAdapter(api_key)
