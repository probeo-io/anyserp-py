from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from anyserp.providers import create_serper_adapter, create_searchapi_adapter


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response (sync .json() method)."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.reason_phrase = "OK" if status_code < 400 else "Error"
    mock_resp.json.return_value = json_data
    return mock_resp


class TestSerperAdapter:
    @pytest.mark.asyncio
    async def test_web_search_response_mapping(self) -> None:
        adapter = create_serper_adapter("test-key")

        mock_data = {
            "organic": [
                {
                    "title": "Python.org",
                    "link": "https://www.python.org",
                    "snippet": "The official Python website",
                    "domain": "python.org",
                    "date": "2024-01-15",
                },
                {
                    "title": "Python Tutorial",
                    "link": "https://docs.python.org/3/tutorial/",
                    "snippet": "The Python Tutorial",
                    "domain": "docs.python.org",
                },
            ],
            "searchParameters": {"timeTaken": 0.35},
            "relatedSearches": [{"query": "python download"}, {"query": "python 3"}],
            "peopleAlsoAsk": [
                {
                    "question": "What is Python?",
                    "snippet": "Python is a programming language",
                    "title": "About Python",
                    "link": "https://example.com/about",
                },
            ],
            "knowledgeGraph": {
                "title": "Python",
                "type": "Programming language",
                "description": "A high-level programming language",
                "descriptionSource": "Wikipedia",
                "descriptionLink": "https://en.wikipedia.org/wiki/Python",
                "imageUrl": "https://example.com/python.png",
                "attributes": {"designer": "Guido van Rossum"},
            },
            "answerBox": {
                "snippet": "Python is a programming language",
                "title": "Python",
                "link": "https://python.org",
            },
        }

        mock_resp = _mock_response(mock_data)

        with patch("anyserp.providers._serper.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await adapter.search({"query": "python"})

        assert result["provider"] == "serper"
        assert result["query"] == "python"
        assert len(result["results"]) == 2
        assert result["results"][0]["position"] == 1
        assert result["results"][0]["title"] == "Python.org"
        assert result["results"][0]["url"] == "https://www.python.org"
        assert result["results"][0]["description"] == "The official Python website"
        assert result["results"][0]["domain"] == "python.org"
        assert result["results"][0]["datePublished"] == "2024-01-15"
        assert result["results"][1]["position"] == 2
        assert result["searchTime"] == 350.0
        assert result["relatedSearches"] == ["python download", "python 3"]
        assert len(result["peopleAlsoAsk"]) == 1
        assert result["peopleAlsoAsk"][0]["question"] == "What is Python?"
        assert result["knowledgePanel"]["title"] == "Python"
        assert result["knowledgePanel"]["type"] == "Programming language"
        assert result["knowledgePanel"]["attributes"] == {"designer": "Guido van Rossum"}
        assert result["answerBox"]["snippet"] == "Python is a programming language"

    @pytest.mark.asyncio
    async def test_image_search_response_mapping(self) -> None:
        adapter = create_serper_adapter("test-key")

        mock_data = {
            "images": [
                {
                    "title": "Python Logo",
                    "link": "https://example.com/page",
                    "snippet": "Python logo image",
                    "imageUrl": "https://example.com/image.png",
                    "imageWidth": 800,
                    "imageHeight": 600,
                    "domain": "example.com",
                    "thumbnailUrl": "https://example.com/thumb.png",
                },
            ],
        }

        mock_resp = _mock_response(mock_data)

        with patch("anyserp.providers._serper.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await adapter.search({"query": "python logo", "type": "images"})

        assert result["provider"] == "serper"
        assert len(result["results"]) == 1
        r = result["results"][0]
        assert r["imageUrl"] == "https://example.com/image.png"
        assert r["imageWidth"] == 800
        assert r["imageHeight"] == 600
        assert r["thumbnail"] == "https://example.com/thumb.png"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        adapter = create_serper_adapter("bad-key")

        mock_resp = _mock_response({"message": "Invalid API key"}, status_code=401)

        with patch("anyserp.providers._serper.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from anyserp import AnySerpError
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 401
            assert "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_supports_all_types(self) -> None:
        adapter = create_serper_adapter("test-key")
        assert adapter.supports_type("web") is True
        assert adapter.supports_type("images") is True
        assert adapter.supports_type("news") is True
        assert adapter.supports_type("videos") is True

    @pytest.mark.asyncio
    async def test_name_property(self) -> None:
        adapter = create_serper_adapter("test-key")
        assert adapter.name == "serper"


class TestSearchApiAdapter:
    @pytest.mark.asyncio
    async def test_web_search_response_mapping(self) -> None:
        adapter = create_searchapi_adapter("test-key")

        mock_data = {
            "organic_results": [
                {
                    "title": "Python.org",
                    "link": "https://www.python.org",
                    "snippet": "The official Python website",
                    "displayed_link": "www.python.org",
                },
            ],
            "search_information": {
                "total_results": 1000000,
                "time_taken_displayed": "0.5",
            },
            "related_searches": [{"query": "python tutorial"}],
            "people_also_ask": [
                {
                    "question": "Is Python easy to learn?",
                    "snippet": "Yes, Python is beginner-friendly",
                    "title": "Learning Python",
                    "link": "https://example.com",
                },
            ],
            "knowledge_graph": {
                "title": "Python",
                "type": "Programming language",
                "description": "A programming language",
                "source": {"name": "Wikipedia", "link": "https://wikipedia.org"},
                "image": "https://example.com/python.png",
            },
            "answer_box": {
                "snippet": "Python is a language",
                "title": "Python",
                "link": "https://python.org",
            },
        }

        mock_resp = _mock_response(mock_data)

        with patch("anyserp.providers._searchapi.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await adapter.search({"query": "python"})

        assert result["provider"] == "searchapi"
        assert result["query"] == "python"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Python.org"
        assert result["totalResults"] == 1000000
        assert result["searchTime"] == 500.0
        assert result["relatedSearches"] == ["python tutorial"]
        assert len(result["peopleAlsoAsk"]) == 1
        assert result["peopleAlsoAsk"][0]["question"] == "Is Python easy to learn?"
        assert result["knowledgePanel"]["title"] == "Python"
        assert result["knowledgePanel"]["source"] == "Wikipedia"
        assert result["knowledgePanel"]["sourceUrl"] == "https://wikipedia.org"
        assert result["answerBox"]["snippet"] == "Python is a language"

    @pytest.mark.asyncio
    async def test_ai_overview_with_include_flag(self) -> None:
        adapter = create_searchapi_adapter("test-key")

        # First call returns search results with page_token
        search_data = {
            "organic_results": [
                {"title": "Result 1", "link": "https://example.com", "snippet": "A result"},
            ],
            "ai_overview": {"page_token": "abc123"},
        }

        # Second call returns AI overview data
        ai_data = {
            "markdown": "# AI Overview\nPython is a language.",
            "text_blocks": [
                {
                    "type": "paragraph",
                    "answer": "Python is a high-level programming language.",
                    "answer_highlight": "high-level programming language",
                    "reference_indexes": [1, 2],
                },
                {
                    "type": "ordered_list",
                    "items": [
                        {"type": "paragraph", "answer": "Easy to learn"},
                        {"type": "paragraph", "answer": "Versatile"},
                    ],
                },
            ],
            "reference_links": [
                {
                    "index": 1,
                    "title": "Python.org",
                    "link": "https://python.org",
                    "snippet": "Official site",
                    "source": "python.org",
                },
                {
                    "index": 2,
                    "title": "Wikipedia",
                    "link": "https://wikipedia.org/python",
                    "date": "2024-01-01",
                    "thumbnail": "https://example.com/thumb.jpg",
                },
            ],
        }

        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_response(search_data)
            else:
                return _mock_response(ai_data)

        with patch("anyserp.providers._searchapi.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await adapter.search({"query": "python", "includeAiOverview": True})

        assert "aiOverview" in result
        ai = result["aiOverview"]
        assert ai["markdown"] == "# AI Overview\nPython is a language."
        assert ai["pageToken"] == "abc123"
        assert len(ai["textBlocks"]) == 2
        assert ai["textBlocks"][0]["type"] == "paragraph"
        assert ai["textBlocks"][0]["answer"] == "Python is a high-level programming language."
        assert ai["textBlocks"][0]["answerHighlight"] == "high-level programming language"
        assert ai["textBlocks"][0]["referenceIndexes"] == [1, 2]
        assert ai["textBlocks"][1]["type"] == "ordered_list"
        assert len(ai["textBlocks"][1]["items"]) == 2
        assert len(ai["references"]) == 2
        assert ai["references"][0]["title"] == "Python.org"
        assert ai["references"][0]["url"] == "https://python.org"
        assert ai["references"][1]["date"] == "2024-01-01"

    @pytest.mark.asyncio
    async def test_ai_overview_token_only_without_include_flag(self) -> None:
        adapter = create_searchapi_adapter("test-key")

        mock_data = {
            "organic_results": [],
            "ai_overview": {"page_token": "xyz789"},
        }

        mock_resp = _mock_response(mock_data)

        with patch("anyserp.providers._searchapi.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await adapter.search({"query": "python"})

        assert "aiOverview" in result
        assert result["aiOverview"]["pageToken"] == "xyz789"
        assert result["aiOverview"]["textBlocks"] == []
        assert result["aiOverview"]["references"] == []

    @pytest.mark.asyncio
    async def test_no_ai_overview_when_no_token(self) -> None:
        adapter = create_searchapi_adapter("test-key")

        mock_data = {"organic_results": []}

        mock_resp = _mock_response(mock_data)

        with patch("anyserp.providers._searchapi.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await adapter.search({"query": "python"})

        assert "aiOverview" not in result
