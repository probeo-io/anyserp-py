from __future__ import annotations

from typing import Any

import httpx

from .._errors import AnySerpError

SEARCHCANS_API_BASE = "https://www.searchcans.com/api/search"


class _SearchCansAdapter:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "searchcans"

    def supports_type(self, search_type: str) -> bool:
        return search_type in ("web", "news")

    async def _make_request(self, body: dict[str, Any]) -> Any:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                SEARCHCANS_API_BASE,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
                json=body,
            )

        if res.status_code >= 400:
            try:
                error_body = res.json()
            except Exception:
                error_body = {"message": res.reason_phrase}
            raise AnySerpError(
                res.status_code,
                error_body.get("error", res.reason_phrase or "Unknown error"),
                {"provider_name": "searchcans", "raw": error_body},
            )
        return res.json()

    async def search(self, request: dict[str, Any]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "s": request["query"],
            "t": "google",
        }

        if request.get("page"):
            body["p"] = request["page"]
        if request.get("country"):
            body["gl"] = request["country"]
        if request.get("language"):
            body["hl"] = request["language"]

        data = await self._make_request(body)

        results: list[dict[str, Any]] = []
        organic = data.get("organic_results") or data.get("results") or []
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

        response: dict[str, Any] = {
            "provider": "searchcans",
            "query": request["query"],
            "results": results,
        }

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

        kp = data.get("knowledge_panel")
        if kp:
            panel: dict[str, Any] = {"title": kp.get("title", "")}
            if kp.get("type"):
                panel["type"] = kp["type"]
            if kp.get("description"):
                panel["description"] = kp["description"]
            response["knowledgePanel"] = panel

        return response


def create_searchcans_adapter(api_key: str) -> _SearchCansAdapter:
    return _SearchCansAdapter(api_key)
