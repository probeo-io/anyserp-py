from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from .._errors import AnySerpError

SEARCHAPI_BASE = "https://www.searchapi.io/api/v1/search"

ENGINE_MAP: dict[str, str] = {
    "web": "google",
    "images": "google_images",
    "news": "google_news",
    "videos": "google_videos",
}

TIME_PERIOD_MAP: dict[str, str] = {
    "day": "last_day",
    "week": "last_week",
    "month": "last_month",
    "year": "last_year",
}


class _SearchApiAdapter:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "searchapi"

    def supports_type(self, search_type: str) -> bool:
        return True

    async def _make_request(self, params: dict[str, str]) -> Any:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                SEARCHAPI_BASE,
                params=params,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept": "application/json",
                },
            )

        if res.status_code >= 400:
            try:
                error_body = res.json()
            except Exception:
                error_body = {"message": res.reason_phrase}
            raise AnySerpError(
                res.status_code,
                error_body.get("error", res.reason_phrase or "Unknown error"),
                {"provider_name": "searchapi", "raw": error_body},
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
                if r.get("displayed_link") and r.get("link"):
                    try:
                        result["domain"] = urlparse(r["link"]).hostname
                    except Exception:
                        pass
                if r.get("date"):
                    result["datePublished"] = r["date"]
                if r.get("thumbnail"):
                    result["thumbnail"] = r["thumbnail"]
                results.append(result)
        elif search_type == "images":
            for i, r in enumerate(data.get("images") or data.get("image_results", [])):
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link") or r.get("original", ""),
                    "description": r.get("snippet") or r.get("title", ""),
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
            for i, r in enumerate(data.get("news_results") or data.get("organic_results", [])):
                source = r.get("source")
                if isinstance(source, dict):
                    source = source.get("name")
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet", ""),
                }
                if source:
                    result["source"] = source
                if r.get("date"):
                    result["datePublished"] = r["date"]
                if r.get("thumbnail"):
                    result["thumbnail"] = r["thumbnail"]
                results.append(result)
        elif search_type == "videos":
            for i, r in enumerate(data.get("video_results", [])):
                channel = r.get("channel")
                if isinstance(channel, dict):
                    channel = channel.get("name")
                result = {
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "description": r.get("snippet") or r.get("description", ""),
                }
                if r.get("duration"):
                    result["duration"] = r["duration"]
                if channel:
                    result["channel"] = channel
                if r.get("thumbnail"):
                    result["thumbnail"] = r["thumbnail"]
                if r.get("date"):
                    result["datePublished"] = r["date"]
                results.append(result)

        response: dict[str, Any] = {
            "provider": "searchapi",
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

        # AI Overview
        page_token = (data.get("ai_overview") or {}).get("page_token")
        if page_token and request.get("includeAiOverview"):
            try:
                ai_data = await self._make_request({
                    "engine": "google_ai_overview",
                    "page_token": page_token,
                })
                response["aiOverview"] = _map_ai_overview(ai_data, page_token)
            except Exception:
                pass  # AI overview fetch failed -- don't fail the whole search
        elif page_token:
            response["aiOverview"] = {
                "textBlocks": [],
                "references": [],
                "pageToken": page_token,
            }

        return response


def _map_text_block(block: dict[str, Any]) -> dict[str, Any]:
    mapped: dict[str, Any] = {"type": block.get("type", "paragraph")}

    if block.get("answer"):
        mapped["answer"] = block["answer"]
    if block.get("answer_highlight"):
        mapped["answerHighlight"] = block["answer_highlight"]
    if block.get("link"):
        mapped["link"] = block["link"]
    if block.get("reference_indexes"):
        mapped["referenceIndexes"] = block["reference_indexes"]
    if block.get("related_searches"):
        mapped["relatedSearches"] = [
            {"query": rs.get("query", ""), **({"link": rs["link"]} if rs.get("link") else {})}
            for rs in block["related_searches"]
        ]

    # Nested items (lists)
    if block.get("items"):
        mapped["items"] = [_map_text_block(item) for item in block["items"]]

    # Table
    if block.get("table"):
        mapped["table"] = {
            "headers": block["table"].get("headers", []),
            "rows": block["table"].get("rows", []),
        }

    # Code
    if block.get("type") == "code_blocks":
        if block.get("language"):
            mapped["language"] = block["language"]
        if block.get("code"):
            mapped["code"] = block["code"]

    # Video
    if block.get("type") == "video":
        mapped["video"] = {
            "title": block.get("title"),
            "link": block.get("link"),
            "duration": block.get("duration"),
            "source": block.get("source"),
            "channel": block.get("channel"),
        }

    return mapped


def _map_ai_overview(data: dict[str, Any], page_token: str) -> dict[str, Any]:
    text_blocks = [_map_text_block(b) for b in data.get("text_blocks", [])]

    references = [
        {
            "index": ref.get("index"),
            **({"title": ref["title"]} if ref.get("title") else {}),
            **({"url": ref["link"]} if ref.get("link") else {}),
            **({"snippet": ref["snippet"]} if ref.get("snippet") else {}),
            **({"date": ref["date"]} if ref.get("date") else {}),
            **({"source": ref["source"]} if ref.get("source") else {}),
            **({"thumbnail": ref["thumbnail"]} if ref.get("thumbnail") else {}),
        }
        for ref in data.get("reference_links", [])
    ]

    result: dict[str, Any] = {
        "textBlocks": text_blocks,
        "references": references,
        "pageToken": page_token,
    }
    if data.get("markdown"):
        result["markdown"] = data["markdown"]

    return result


def create_searchapi_adapter(api_key: str) -> _SearchApiAdapter:
    return _SearchApiAdapter(api_key)
