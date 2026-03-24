from __future__ import annotations

import base64
from typing import Any

import httpx

from .._errors import AnySerpError

DATAFORSEO_API_BASE = "https://api.dataforseo.com/v3"

COUNTRY_LOCATION_MAP: dict[str, int] = {
    "us": 2840, "gb": 2826, "ca": 2124, "au": 2036, "de": 2276, "fr": 2250,
    "es": 2724, "it": 2380, "br": 2076, "in": 2356, "jp": 2392, "kr": 2410,
    "mx": 2484, "nl": 2528, "se": 2752, "no": 2578, "dk": 2208, "fi": 2246,
    "pl": 2616, "ru": 2643, "za": 2710, "ar": 2032, "cl": 2152, "co": 2170,
    "pt": 2620, "be": 2056, "at": 2040, "ch": 2756, "ie": 2372, "nz": 2554,
    "sg": 2702, "hk": 2344, "tw": 2158, "ph": 2608, "th": 2764, "my": 2458,
    "id": 2360, "vn": 2704, "tr": 2792, "il": 2376, "ae": 2784, "sa": 2682,
    "eg": 2818, "ng": 2566, "ke": 2404,
}

SE_TYPE_MAP: dict[str, str] = {
    "web": "organic",
    "images": "organic",
    "news": "news",
    "videos": "organic",
}


class _DataForSeoAdapter:
    def __init__(self, login: str, password: str) -> None:
        creds = base64.b64encode(f"{login}:{password}".encode()).decode()
        self._auth_header = f"Basic {creds}"

    @property
    def name(self) -> str:
        return "dataforseo"

    def supports_type(self, search_type: str) -> bool:
        return search_type in ("web", "news")

    async def _make_request(self, path: str, tasks: list[dict[str, Any]]) -> Any:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{DATAFORSEO_API_BASE}{path}",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": self._auth_header,
                },
                json=tasks,
            )

        if res.status_code >= 400:
            try:
                error_body = res.json()
            except Exception:
                error_body = {"message": res.reason_phrase}
            raise AnySerpError(
                res.status_code,
                error_body.get("status_message", res.reason_phrase or "Unknown error"),
                {"provider_name": "dataforseo", "raw": error_body},
            )

        data = res.json()

        if data.get("status_code") and data["status_code"] >= 40000:
            raise AnySerpError(
                502 if data["status_code"] >= 50000 else 400,
                data.get("status_message", "DataForSEO error"),
                {"provider_name": "dataforseo", "raw": data},
            )

        task = (data.get("tasks") or [None])[0]
        if not task:
            raise AnySerpError(502, "No task in DataForSEO response", {"provider_name": "dataforseo", "raw": data})

        if task.get("status_code", 0) >= 40000:
            raise AnySerpError(
                502 if task["status_code"] >= 50000 else 400,
                task.get("status_message", "DataForSEO task error"),
                {"provider_name": "dataforseo", "raw": task},
            )

        return task

    async def search(self, request: dict[str, Any]) -> dict[str, Any]:
        search_type = request.get("type", "web")
        se_type = SE_TYPE_MAP[search_type]
        path = f"/serp/google/{se_type}/live/advanced"

        task: dict[str, Any] = {
            "keyword": request["query"],
            "depth": request.get("num") or 10,
        }

        if request.get("country"):
            loc_code = COUNTRY_LOCATION_MAP.get(request["country"].lower())
            if loc_code:
                task["location_code"] = loc_code
        if request.get("language"):
            task["language_code"] = request["language"]
        if request.get("page") and request["page"] > 1:
            task["depth"] = (request.get("num") or 10) * request["page"]

        task_result = await self._make_request(path, [task])
        result_data = ((task_result.get("result") or [None])[0]) or {}

        results: list[dict[str, Any]] = []
        knowledge_panel: dict[str, Any] | None = None
        answer_box: dict[str, Any] | None = None

        items = result_data.get("items", [])
        if items:
            position = 0
            for item in items:
                item_type = item.get("type")
                if item_type == "organic":
                    position += 1
                    result: dict[str, Any] = {
                        "position": position,
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("description", ""),
                    }
                    if item.get("domain"):
                        result["domain"] = item["domain"]
                    if item.get("timestamp"):
                        result["datePublished"] = item["timestamp"]
                    results.append(result)
                elif item_type == "knowledge_graph":
                    knowledge_panel = {"title": item.get("title", "")}
                    if item.get("sub_title"):
                        knowledge_panel["type"] = item["sub_title"]
                    if item.get("description"):
                        knowledge_panel["description"] = item["description"]
                    if item.get("image_url"):
                        knowledge_panel["imageUrl"] = item["image_url"]
                elif item_type == "featured_snippet":
                    answer_box = {
                        "snippet": item.get("description") or item.get("title", ""),
                    }
                    if item.get("title"):
                        answer_box["title"] = item["title"]
                    if item.get("url"):
                        answer_box["url"] = item["url"]
                elif item_type == "news_search" and search_type == "news":
                    position += 1
                    result = {
                        "position": position,
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("snippet") or item.get("description", ""),
                    }
                    if item.get("source"):
                        result["source"] = item["source"]
                    if item.get("timestamp") or item.get("datetime"):
                        result["datePublished"] = item.get("timestamp") or item.get("datetime")
                    if item.get("image_url"):
                        result["thumbnail"] = item["image_url"]
                    results.append(result)

        response: dict[str, Any] = {
            "provider": "dataforseo",
            "query": request["query"],
            "results": results,
        }

        if result_data.get("se_results_count"):
            response["totalResults"] = result_data["se_results_count"]
        if knowledge_panel:
            response["knowledgePanel"] = knowledge_panel
        if answer_box:
            response["answerBox"] = answer_box

        paa_items = [i for i in items if i.get("type") == "people_also_ask"]
        if paa_items:
            questions: list[dict[str, Any]] = []
            for paa in paa_items:
                for q in paa.get("items", []):
                    entry: dict[str, Any] = {"question": q.get("title", "")}
                    if q.get("description"):
                        entry["snippet"] = q["description"]
                    if q.get("url"):
                        entry["url"] = q["url"]
                    questions.append(entry)
            if questions:
                response["peopleAlsoAsk"] = questions

        return response


def create_dataforseo_adapter(login: str, password: str) -> _DataForSeoAdapter:
    return _DataForSeoAdapter(login, password)
