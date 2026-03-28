from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from anyserp import AnySerpError
from anyserp.providers import (
    create_bing_adapter,
    create_brave_adapter,
    create_brightdata_adapter,
    create_dataforseo_adapter,
    create_google_adapter,
    create_scrapingdog_adapter,
    create_searchapi_adapter,
    create_searchcans_adapter,
    create_serpapi_adapter,
    create_serper_adapter,
    create_valueserp_adapter,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response (sync .json() method)."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.reason_phrase = "OK" if status_code < 400 else "Error"
    mock_resp.json.return_value = json_data
    return mock_resp


def _patch_post(module_path: str):
    """Return a context-manager that patches httpx.AsyncClient for POST."""
    return _PatchClient(module_path, "post")


def _patch_get(module_path: str):
    """Return a context-manager that patches httpx.AsyncClient for GET."""
    return _PatchClient(module_path, "get")


class _PatchClient:
    """Thin wrapper around patch for httpx.AsyncClient."""

    def __init__(self, module_path: str, method: str) -> None:
        self._module_path = module_path
        self._method = method
        self._patcher = None
        self._mock_client = None

    def __call__(self, mock_resp):
        self._mock_resp = mock_resp
        return self

    def __enter__(self):
        self._patcher = patch(f"{self._module_path}.httpx.AsyncClient")
        mock_cls = self._patcher.__enter__()
        self._mock_client = AsyncMock()
        getattr(self._mock_client, self._method).return_value = self._mock_resp
        self._mock_client.__aenter__ = AsyncMock(return_value=self._mock_client)
        self._mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = self._mock_client
        return self._mock_client

    def __exit__(self, *args):
        return self._patcher.__exit__(*args)


def _make_post_ctx(module: str, resp: MagicMock):
    """Build a patch context for a POST-based provider."""
    return _build_ctx(module, "post", resp)


def _make_get_ctx(module: str, resp: MagicMock):
    """Build a patch context for a GET-based provider."""
    return _build_ctx(module, "get", resp)


def _build_ctx(module: str, method: str, resp: MagicMock):
    """Build a patch context for any HTTP method."""
    p = patch(f"anyserp.providers.{module}.httpx.AsyncClient")

    class Ctx:
        def __enter__(self_inner):
            self_inner._patcher = p
            mock_cls = p.__enter__()
            self_inner.client = AsyncMock()
            getattr(self_inner.client, method).return_value = resp
            self_inner.client.__aenter__ = AsyncMock(return_value=self_inner.client)
            self_inner.client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = self_inner.client
            return self_inner.client

        def __exit__(self_inner, *a):
            return p.__exit__(*a)

    return Ctx()


# ── Serper ───────────────────────────────────────────────────────────────────


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
        with _make_post_ctx("_serper", _mock_response(mock_data)) as client:
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
        with _make_post_ctx("_serper", _mock_response(mock_data)):
            result = await adapter.search({"query": "python logo", "type": "images"})

        assert result["provider"] == "serper"
        r = result["results"][0]
        assert r["imageUrl"] == "https://example.com/image.png"
        assert r["imageWidth"] == 800
        assert r["imageHeight"] == 600
        assert r["thumbnail"] == "https://example.com/thumb.png"

    @pytest.mark.asyncio
    async def test_news_search_response_mapping(self) -> None:
        adapter = create_serper_adapter("test-key")
        mock_data = {
            "news": [
                {
                    "title": "Python 3.13 Released",
                    "link": "https://news.example.com/python",
                    "snippet": "New version available",
                    "source": "Tech News",
                    "date": "2024-10-01",
                    "imageUrl": "https://example.com/news-thumb.png",
                },
            ],
        }
        with _make_post_ctx("_serper", _mock_response(mock_data)):
            result = await adapter.search({"query": "python news", "type": "news"})

        r = result["results"][0]
        assert r["source"] == "Tech News"
        assert r["datePublished"] == "2024-10-01"
        assert r["thumbnail"] == "https://example.com/news-thumb.png"

    @pytest.mark.asyncio
    async def test_video_search_response_mapping(self) -> None:
        adapter = create_serper_adapter("test-key")
        mock_data = {
            "videos": [
                {
                    "title": "Learn Python",
                    "link": "https://youtube.com/watch?v=abc",
                    "snippet": "A tutorial",
                    "duration": "15:30",
                    "channel": "CodeChannel",
                    "imageUrl": "https://example.com/vid-thumb.png",
                    "date": "2024-06-01",
                },
            ],
        }
        with _make_post_ctx("_serper", _mock_response(mock_data)):
            result = await adapter.search({"query": "python tutorial", "type": "videos"})

        r = result["results"][0]
        assert r["duration"] == "15:30"
        assert r["channel"] == "CodeChannel"
        assert r["thumbnail"] == "https://example.com/vid-thumb.png"
        assert r["datePublished"] == "2024-06-01"

    @pytest.mark.asyncio
    async def test_request_params_forwarded(self) -> None:
        adapter = create_serper_adapter("test-key")
        mock_data = {"organic": []}
        with _make_post_ctx("_serper", _mock_response(mock_data)) as client:
            await adapter.search({
                "query": "test",
                "num": 5,
                "page": 2,
                "country": "gb",
                "language": "en",
                "dateRange": "week",
            })
            body = client.post.call_args[1]["json"]
            assert body["q"] == "test"
            assert body["num"] == 5
            assert body["page"] == 2
            assert body["gl"] == "gb"
            assert body["hl"] == "en"
            assert body["tbs"] == "qdr:w"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        adapter = create_serper_adapter("bad-key")
        with _make_post_ctx("_serper", _mock_response({"message": "Invalid API key"}, 401)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 401
            assert "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_with_unparseable_json(self) -> None:
        adapter = create_serper_adapter("bad-key")
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.reason_phrase = "Internal Server Error"
        mock_resp.json.side_effect = ValueError("not json")
        with _make_post_ctx("_serper", mock_resp):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 500

    def test_supports_all_types(self) -> None:
        adapter = create_serper_adapter("test-key")
        for t in ("web", "images", "news", "videos"):
            assert adapter.supports_type(t) is True

    def test_name_property(self) -> None:
        adapter = create_serper_adapter("test-key")
        assert adapter.name == "serper"

    @pytest.mark.asyncio
    async def test_api_key_header(self) -> None:
        adapter = create_serper_adapter("my-secret-key")
        with _make_post_ctx("_serper", _mock_response({"organic": []})) as client:
            await adapter.search({"query": "test"})
            headers = client.post.call_args[1]["headers"]
            assert headers["X-API-KEY"] == "my-secret-key"

    @pytest.mark.asyncio
    async def test_correct_endpoint_per_type(self) -> None:
        adapter = create_serper_adapter("k")
        expected = {
            "web": "/search",
            "images": "/images",
            "news": "/news",
            "videos": "/videos",
        }
        for search_type, endpoint in expected.items():
            resp_key = {"web": "organic", "images": "images", "news": "news", "videos": "videos"}
            with _make_post_ctx("_serper", _mock_response({resp_key[search_type]: []})) as client:
                await adapter.search({"query": "q", "type": search_type})
                url = client.post.call_args[0][0]
                assert url.endswith(endpoint)


# ── SerpAPI ──────────────────────────────────────────────────────────────────


class TestSerpApiAdapter:
    @pytest.mark.asyncio
    async def test_web_search_response_mapping(self) -> None:
        adapter = create_serpapi_adapter("test-key")
        mock_data = {
            "organic_results": [
                {
                    "position": 1,
                    "title": "Python.org",
                    "link": "https://www.python.org",
                    "snippet": "Official site",
                    "displayed_link": "www.python.org",
                    "date": "2024-01-01",
                    "thumbnail": "https://example.com/thumb.png",
                },
            ],
            "search_information": {"total_results": 500000, "time_taken_displayed": "0.42"},
            "related_searches": [{"query": "python docs"}],
            "related_questions": [
                {"question": "What is Python?", "snippet": "A language", "title": "Python", "link": "https://ex.com"},
            ],
            "knowledge_graph": {
                "title": "Python",
                "type": "Language",
                "description": "High-level lang",
                "source": {"name": "Wikipedia", "link": "https://wiki.org"},
                "header_images": [{"image": "https://ex.com/img.png"}],
            },
            "answer_box": {"snippet": "Python is great", "title": "Python", "link": "https://python.org"},
        }
        with _make_get_ctx("_serpapi", _mock_response(mock_data)):
            result = await adapter.search({"query": "python"})

        assert result["provider"] == "serpapi"
        assert result["totalResults"] == 500000
        assert result["searchTime"] == 420.0
        assert result["results"][0]["title"] == "Python.org"
        assert result["results"][0]["datePublished"] == "2024-01-01"
        assert result["results"][0]["thumbnail"] == "https://example.com/thumb.png"
        assert result["relatedSearches"] == ["python docs"]
        assert result["peopleAlsoAsk"][0]["question"] == "What is Python?"
        assert result["knowledgePanel"]["source"] == "Wikipedia"
        assert result["knowledgePanel"]["sourceUrl"] == "https://wiki.org"
        assert result["knowledgePanel"]["imageUrl"] == "https://ex.com/img.png"
        assert result["answerBox"]["snippet"] == "Python is great"

    @pytest.mark.asyncio
    async def test_image_search(self) -> None:
        adapter = create_serpapi_adapter("test-key")
        mock_data = {
            "images_results": [
                {
                    "title": "Img",
                    "link": "https://ex.com",
                    "original": "https://ex.com/full.png",
                    "original_width": 1920,
                    "original_height": 1080,
                    "thumbnail": "https://ex.com/thumb.png",
                    "source": "example.com",
                },
            ],
        }
        with _make_get_ctx("_serpapi", _mock_response(mock_data)):
            result = await adapter.search({"query": "img", "type": "images"})

        r = result["results"][0]
        assert r["imageUrl"] == "https://ex.com/full.png"
        assert r["imageWidth"] == 1920
        assert r["imageHeight"] == 1080
        assert r["source"] == "example.com"

    @pytest.mark.asyncio
    async def test_news_search_dict_source(self) -> None:
        adapter = create_serpapi_adapter("test-key")
        mock_data = {
            "news_results": [
                {
                    "title": "News",
                    "link": "https://ex.com",
                    "snippet": "Breaking",
                    "source": {"name": "CNN"},
                    "date": "2024-03-01",
                },
            ],
        }
        with _make_get_ctx("_serpapi", _mock_response(mock_data)):
            result = await adapter.search({"query": "news", "type": "news"})

        assert result["results"][0]["source"] == "CNN"

    @pytest.mark.asyncio
    async def test_video_search_dict_channel_and_thumbnail(self) -> None:
        adapter = create_serpapi_adapter("test-key")
        mock_data = {
            "video_results": [
                {
                    "title": "Vid",
                    "link": "https://yt.com",
                    "duration": "5:00",
                    "channel": {"name": "MyChannel"},
                    "thumbnail": {"static": "https://ex.com/static.png"},
                    "date": "2024-01-01",
                },
            ],
        }
        with _make_get_ctx("_serpapi", _mock_response(mock_data)):
            result = await adapter.search({"query": "vid", "type": "videos"})

        r = result["results"][0]
        assert r["channel"] == "MyChannel"
        assert r["thumbnail"] == "https://ex.com/static.png"

    @pytest.mark.asyncio
    async def test_request_params(self) -> None:
        adapter = create_serpapi_adapter("test-key")
        with _make_get_ctx("_serpapi", _mock_response({"organic_results": []})) as client:
            await adapter.search({
                "query": "test",
                "num": 10,
                "page": 3,
                "country": "us",
                "language": "en",
                "safe": True,
                "dateRange": "month",
            })
            params = client.get.call_args[1]["params"]
            assert params["q"] == "test"
            assert params["num"] == "10"
            assert params["start"] == "20"
            assert params["gl"] == "us"
            assert params["hl"] == "en"
            assert params["safe"] == "active"
            assert params["tbs"] == "qdr:m"
            assert params["api_key"] == "test-key"
            assert params["engine"] == "google"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        adapter = create_serpapi_adapter("bad")
        with _make_get_ctx("_serpapi", _mock_response({"error": "Bad key"}, 403)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 403

    def test_name_and_supports_type(self) -> None:
        adapter = create_serpapi_adapter("k")
        assert adapter.name == "serpapi"
        assert adapter.supports_type("web") is True


# ── Google CSE ───────────────────────────────────────────────────────────────


class TestGoogleAdapter:
    @pytest.mark.asyncio
    async def test_web_search_response_mapping(self) -> None:
        adapter = create_google_adapter("key", "engine")
        mock_data = {
            "items": [
                {
                    "title": "Python.org",
                    "link": "https://www.python.org",
                    "snippet": "Official site",
                    "displayLink": "www.python.org",
                    "pagemap": {"metatags": [{"article:published_time": "2024-01-01"}]},
                },
            ],
            "searchInformation": {"totalResults": "1000000", "searchTime": 0.25},
        }
        with _make_get_ctx("_google", _mock_response(mock_data)):
            result = await adapter.search({"query": "python"})

        assert result["provider"] == "google"
        assert result["totalResults"] == 1000000
        assert result["searchTime"] == 250.0
        assert result["results"][0]["domain"] == "www.python.org"
        assert result["results"][0]["datePublished"] == "2024-01-01"

    @pytest.mark.asyncio
    async def test_image_search(self) -> None:
        adapter = create_google_adapter("key", "engine")
        mock_data = {
            "items": [
                {
                    "title": "Img",
                    "link": "https://ex.com/img.png",
                    "snippet": "An image",
                    "image": {
                        "width": 640,
                        "height": 480,
                        "thumbnailLink": "https://ex.com/thumb.png",
                    },
                },
            ],
        }
        with _make_get_ctx("_google", _mock_response(mock_data)):
            result = await adapter.search({"query": "img", "type": "images"})

        r = result["results"][0]
        assert r["imageUrl"] == "https://ex.com/img.png"
        assert r["imageWidth"] == 640
        assert r["imageHeight"] == 480
        assert r["thumbnail"] == "https://ex.com/thumb.png"

    @pytest.mark.asyncio
    async def test_request_params(self) -> None:
        adapter = create_google_adapter("key", "engine")
        with _make_get_ctx("_google", _mock_response({"items": []})) as client:
            await adapter.search({
                "query": "test",
                "num": 10,
                "page": 2,
                "country": "gb",
                "language": "en",
                "safe": True,
                "dateRange": "day",
            })
            params = client.get.call_args[1]["params"]
            assert params["q"] == "test"
            assert params["num"] == "10"
            assert params["start"] == "11"
            assert params["gl"] == "gb"
            assert params["lr"] == "lang_en"
            assert params["safe"] == "active"
            assert params["dateRestrict"] == "d1"
            assert params["key"] == "key"
            assert params["cx"] == "engine"

    @pytest.mark.asyncio
    async def test_num_capped_at_10(self) -> None:
        adapter = create_google_adapter("key", "engine")
        with _make_get_ctx("_google", _mock_response({"items": []})) as client:
            await adapter.search({"query": "test", "num": 50})
            params = client.get.call_args[1]["params"]
            assert params["num"] == "10"

    def test_supports_type(self) -> None:
        adapter = create_google_adapter("key", "engine")
        assert adapter.supports_type("web") is True
        assert adapter.supports_type("images") is True
        assert adapter.supports_type("news") is False
        assert adapter.supports_type("videos") is False

    def test_name(self) -> None:
        adapter = create_google_adapter("key", "engine")
        assert adapter.name == "google"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        adapter = create_google_adapter("key", "engine")
        err_body = {"error": {"message": "Quota exceeded"}}
        with _make_get_ctx("_google", _mock_response(err_body, 429)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 429
            assert "Quota exceeded" in str(exc_info.value)


# ── Bing ─────────────────────────────────────────────────────────────────────


class TestBingAdapter:
    @pytest.mark.asyncio
    async def test_web_search_response_mapping(self) -> None:
        adapter = create_bing_adapter("test-key")
        mock_data = {
            "webPages": {
                "totalEstimatedMatches": 500000,
                "value": [
                    {
                        "name": "Python.org",
                        "url": "https://www.python.org",
                        "snippet": "Official site",
                        "displayUrl": "https://www.python.org",
                        "dateLastCrawled": "2024-01-15T00:00:00Z",
                    },
                ],
            },
        }
        with _make_get_ctx("_bing", _mock_response(mock_data)):
            result = await adapter.search({"query": "python"})

        assert result["provider"] == "bing"
        assert result["totalResults"] == 500000
        assert result["results"][0]["title"] == "Python.org"
        assert result["results"][0]["domain"] == "www.python.org"
        assert result["results"][0]["datePublished"] == "2024-01-15T00:00:00Z"

    @pytest.mark.asyncio
    async def test_image_search(self) -> None:
        adapter = create_bing_adapter("test-key")
        mock_data = {
            "totalEstimatedMatches": 100,
            "value": [
                {
                    "name": "Python Logo",
                    "hostPageUrl": "https://ex.com/page",
                    "contentUrl": "https://ex.com/img.png",
                    "width": 800,
                    "height": 600,
                    "thumbnailUrl": "https://ex.com/thumb.png",
                    "hostPageDisplayUrl": "ex.com/page",
                },
            ],
        }
        with _make_get_ctx("_bing", _mock_response(mock_data)):
            result = await adapter.search({"query": "python logo", "type": "images"})

        r = result["results"][0]
        assert r["imageUrl"] == "https://ex.com/img.png"
        assert r["imageWidth"] == 800
        assert r["imageHeight"] == 600
        assert r["thumbnail"] == "https://ex.com/thumb.png"
        assert r["domain"] == "ex.com"

    @pytest.mark.asyncio
    async def test_news_search(self) -> None:
        adapter = create_bing_adapter("test-key")
        mock_data = {
            "value": [
                {
                    "name": "Python News",
                    "url": "https://ex.com/news",
                    "description": "Breaking news",
                    "provider": [{"name": "TechCrunch"}],
                    "datePublished": "2024-06-01",
                    "image": {"thumbnail": {"contentUrl": "https://ex.com/thumb.png"}},
                },
            ],
        }
        with _make_get_ctx("_bing", _mock_response(mock_data)):
            result = await adapter.search({"query": "python news", "type": "news"})

        r = result["results"][0]
        assert r["source"] == "TechCrunch"
        assert r["datePublished"] == "2024-06-01"
        assert r["thumbnail"] == "https://ex.com/thumb.png"

    @pytest.mark.asyncio
    async def test_video_search(self) -> None:
        adapter = create_bing_adapter("test-key")
        mock_data = {
            "value": [
                {
                    "name": "Learn Python",
                    "contentUrl": "https://yt.com/watch",
                    "description": "Tutorial",
                    "duration": "PT15M30S",
                    "creator": {"name": "CodeChannel"},
                    "thumbnailUrl": "https://ex.com/vthumb.png",
                    "datePublished": "2024-03-01",
                },
            ],
        }
        with _make_get_ctx("_bing", _mock_response(mock_data)):
            result = await adapter.search({"query": "python tutorial", "type": "videos"})

        r = result["results"][0]
        assert r["duration"] == "PT15M30S"
        assert r["channel"] == "CodeChannel"
        assert r["thumbnail"] == "https://ex.com/vthumb.png"

    @pytest.mark.asyncio
    async def test_request_params(self) -> None:
        adapter = create_bing_adapter("test-key")
        with _make_get_ctx("_bing", _mock_response({"webPages": {"value": []}})) as client:
            await adapter.search({
                "query": "test",
                "num": 20,
                "page": 3,
                "country": "us",
                "language": "en",
                "safe": True,
                "dateRange": "week",
            })
            params = client.get.call_args[1]["params"]
            assert params["q"] == "test"
            assert params["count"] == "20"
            assert params["offset"] == "40"
            assert params["cc"] == "us"
            assert params["setLang"] == "en"
            assert params["safeSearch"] == "Strict"
            assert params["freshness"] == "Week"

    @pytest.mark.asyncio
    async def test_api_key_header(self) -> None:
        adapter = create_bing_adapter("my-bing-key")
        with _make_get_ctx("_bing", _mock_response({"webPages": {"value": []}})) as client:
            await adapter.search({"query": "test"})
            headers = client.get.call_args[1]["headers"]
            assert headers["Ocp-Apim-Subscription-Key"] == "my-bing-key"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        adapter = create_bing_adapter("bad")
        with _make_get_ctx("_bing", _mock_response({"error": {"message": "Unauthorized"}}, 401)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 401

    def test_name_and_supports_type(self) -> None:
        adapter = create_bing_adapter("k")
        assert adapter.name == "bing"
        assert adapter.supports_type("web") is True
        assert adapter.supports_type("videos") is True


# ── Brave ────────────────────────────────────────────────────────────────────


class TestBraveAdapter:
    @pytest.mark.asyncio
    async def test_web_search_response_mapping(self) -> None:
        adapter = create_brave_adapter("test-key")
        mock_data = {
            "web": {
                "results": [
                    {
                        "title": "Python.org",
                        "url": "https://www.python.org",
                        "description": "Official site",
                        "meta_url": {"hostname": "www.python.org"},
                        "page_age": "2024-01-15",
                        "thumbnail": {"src": "https://ex.com/thumb.png"},
                    },
                ],
            },
            "query": {"related_searches": [{"query": "python tutorial"}]},
        }
        with _make_get_ctx("_brave", _mock_response(mock_data)):
            result = await adapter.search({"query": "python"})

        assert result["provider"] == "brave"
        assert result["results"][0]["domain"] == "www.python.org"
        assert result["results"][0]["datePublished"] == "2024-01-15"
        assert result["results"][0]["thumbnail"] == "https://ex.com/thumb.png"
        assert result["relatedSearches"] == ["python tutorial"]

    @pytest.mark.asyncio
    async def test_image_search(self) -> None:
        adapter = create_brave_adapter("test-key")
        mock_data = {
            "results": [
                {
                    "title": "Img",
                    "url": "https://ex.com/page",
                    "properties": {"url": "https://ex.com/full.png", "width": 1920, "height": 1080},
                    "thumbnail": {"src": "https://ex.com/thumb.png"},
                    "source": "example.com",
                },
            ],
        }
        with _make_get_ctx("_brave", _mock_response(mock_data)):
            result = await adapter.search({"query": "img", "type": "images"})

        r = result["results"][0]
        assert r["imageUrl"] == "https://ex.com/full.png"
        assert r["imageWidth"] == 1920
        assert r["imageHeight"] == 1080
        assert r["source"] == "example.com"

    @pytest.mark.asyncio
    async def test_news_search(self) -> None:
        adapter = create_brave_adapter("test-key")
        mock_data = {
            "results": [
                {
                    "title": "News",
                    "url": "https://ex.com/news",
                    "description": "Breaking",
                    "meta_url": {"hostname": "news.example.com"},
                    "age": "2 hours ago",
                    "thumbnail": {"src": "https://ex.com/nthumb.png"},
                },
            ],
        }
        with _make_get_ctx("_brave", _mock_response(mock_data)):
            result = await adapter.search({"query": "news", "type": "news"})

        r = result["results"][0]
        assert r["source"] == "news.example.com"
        assert r["datePublished"] == "2 hours ago"

    @pytest.mark.asyncio
    async def test_video_search(self) -> None:
        adapter = create_brave_adapter("test-key")
        mock_data = {
            "results": [
                {
                    "title": "Vid",
                    "url": "https://yt.com/watch",
                    "description": "A video",
                    "thumbnail": {"src": "https://ex.com/vthumb.png"},
                    "age": "1 day ago",
                },
            ],
        }
        with _make_get_ctx("_brave", _mock_response(mock_data)):
            result = await adapter.search({"query": "vid", "type": "videos"})

        r = result["results"][0]
        assert r["thumbnail"] == "https://ex.com/vthumb.png"
        assert r["datePublished"] == "1 day ago"

    @pytest.mark.asyncio
    async def test_request_params(self) -> None:
        adapter = create_brave_adapter("test-key")
        with _make_get_ctx("_brave", _mock_response({"web": {"results": []}})) as client:
            await adapter.search({
                "query": "test",
                "num": 15,
                "page": 2,
                "country": "us",
                "language": "en",
                "safe": True,
                "dateRange": "day",
            })
            params = client.get.call_args[1]["params"]
            assert params["q"] == "test"
            assert params["count"] == "15"
            assert params["offset"] == "15"
            assert params["country"] == "us"
            assert params["search_lang"] == "en"
            assert params["safesearch"] == "strict"
            assert params["freshness"] == "pd"

    @pytest.mark.asyncio
    async def test_api_key_header(self) -> None:
        adapter = create_brave_adapter("my-brave-key")
        with _make_get_ctx("_brave", _mock_response({"web": {"results": []}})) as client:
            await adapter.search({"query": "test"})
            headers = client.get.call_args[1]["headers"]
            assert headers["X-Subscription-Token"] == "my-brave-key"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        adapter = create_brave_adapter("bad")
        with _make_get_ctx("_brave", _mock_response({"message": "Forbidden"}, 403)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 403

    def test_name_and_supports_type(self) -> None:
        adapter = create_brave_adapter("k")
        assert adapter.name == "brave"
        assert adapter.supports_type("web") is True


# ── DataForSEO ───────────────────────────────────────────────────────────────


class TestDataForSeoAdapter:
    @pytest.mark.asyncio
    async def test_web_search_response_mapping(self) -> None:
        adapter = create_dataforseo_adapter("user", "pass")
        mock_data = {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [
                        {
                            "se_results_count": 1000000,
                            "items": [
                                {
                                    "type": "organic",
                                    "title": "Python.org",
                                    "url": "https://www.python.org",
                                    "description": "Official site",
                                    "domain": "python.org",
                                    "timestamp": "2024-01-01",
                                },
                                {
                                    "type": "knowledge_graph",
                                    "title": "Python",
                                    "sub_title": "Language",
                                    "description": "A language",
                                    "image_url": "https://ex.com/img.png",
                                },
                                {
                                    "type": "featured_snippet",
                                    "title": "Python",
                                    "description": "Python is great",
                                    "url": "https://python.org",
                                },
                                {
                                    "type": "people_also_ask",
                                    "items": [
                                        {"title": "What is Python?", "description": "A lang", "url": "https://ex.com"},
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
        with _make_post_ctx("_dataforseo", _mock_response(mock_data)):
            result = await adapter.search({"query": "python"})

        assert result["provider"] == "dataforseo"
        assert result["totalResults"] == 1000000
        assert result["results"][0]["title"] == "Python.org"
        assert result["results"][0]["domain"] == "python.org"
        assert result["knowledgePanel"]["title"] == "Python"
        assert result["knowledgePanel"]["type"] == "Language"
        assert result["knowledgePanel"]["imageUrl"] == "https://ex.com/img.png"
        assert result["answerBox"]["snippet"] == "Python is great"
        assert result["answerBox"]["url"] == "https://python.org"
        assert result["peopleAlsoAsk"][0]["question"] == "What is Python?"

    @pytest.mark.asyncio
    async def test_news_search(self) -> None:
        adapter = create_dataforseo_adapter("user", "pass")
        mock_data = {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [
                        {
                            "items": [
                                {
                                    "type": "news_search",
                                    "title": "Breaking",
                                    "url": "https://ex.com/news",
                                    "snippet": "News text",
                                    "source": "CNN",
                                    "timestamp": "2024-06-01",
                                    "image_url": "https://ex.com/thumb.png",
                                },
                            ],
                        },
                    ],
                },
            ],
        }
        with _make_post_ctx("_dataforseo", _mock_response(mock_data)):
            result = await adapter.search({"query": "news", "type": "news"})

        r = result["results"][0]
        assert r["source"] == "CNN"
        assert r["datePublished"] == "2024-06-01"
        assert r["thumbnail"] == "https://ex.com/thumb.png"

    @pytest.mark.asyncio
    async def test_request_params(self) -> None:
        adapter = create_dataforseo_adapter("user", "pass")
        mock_data = {
            "status_code": 20000,
            "tasks": [{"status_code": 20000, "result": [{"items": []}]}],
        }
        with _make_post_ctx("_dataforseo", _mock_response(mock_data)) as client:
            await adapter.search({
                "query": "test",
                "num": 20,
                "country": "us",
                "language": "en",
                "page": 3,
            })
            body = client.post.call_args[1]["json"]
            task = body[0]
            assert task["keyword"] == "test"
            assert task["location_code"] == 2840
            assert task["language_code"] == "en"
            # page > 1: depth = num * page
            assert task["depth"] == 60

    @pytest.mark.asyncio
    async def test_auth_header(self) -> None:
        import base64
        adapter = create_dataforseo_adapter("myuser", "mypass")
        mock_data = {
            "status_code": 20000,
            "tasks": [{"status_code": 20000, "result": [{"items": []}]}],
        }
        with _make_post_ctx("_dataforseo", _mock_response(mock_data)) as client:
            await adapter.search({"query": "test"})
            headers = client.post.call_args[1]["headers"]
            expected = "Basic " + base64.b64encode(b"myuser:mypass").decode()
            assert headers["Authorization"] == expected

    @pytest.mark.asyncio
    async def test_http_error(self) -> None:
        adapter = create_dataforseo_adapter("u", "p")
        with _make_post_ctx("_dataforseo", _mock_response({"status_message": "Auth failed"}, 401)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 401

    @pytest.mark.asyncio
    async def test_api_level_error_code(self) -> None:
        adapter = create_dataforseo_adapter("u", "p")
        mock_data = {"status_code": 40001, "status_message": "Bad request", "tasks": []}
        with _make_post_ctx("_dataforseo", _mock_response(mock_data)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 400

    @pytest.mark.asyncio
    async def test_task_level_error_code(self) -> None:
        adapter = create_dataforseo_adapter("u", "p")
        mock_data = {
            "status_code": 20000,
            "tasks": [{"status_code": 50001, "status_message": "Server error"}],
        }
        with _make_post_ctx("_dataforseo", _mock_response(mock_data)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 502

    @pytest.mark.asyncio
    async def test_no_task_in_response(self) -> None:
        adapter = create_dataforseo_adapter("u", "p")
        mock_data = {"status_code": 20000, "tasks": []}
        with _make_post_ctx("_dataforseo", _mock_response(mock_data)):
            with pytest.raises(AnySerpError, match="No task"):
                await adapter.search({"query": "test"})

    def test_supports_type(self) -> None:
        adapter = create_dataforseo_adapter("u", "p")
        assert adapter.supports_type("web") is True
        assert adapter.supports_type("news") is True
        assert adapter.supports_type("images") is False
        assert adapter.supports_type("videos") is False

    def test_name(self) -> None:
        adapter = create_dataforseo_adapter("u", "p")
        assert adapter.name == "dataforseo"


# ── SearchAPI ────────────────────────────────────────────────────────────────


class TestSearchApiAdapter:
    @pytest.mark.asyncio
    async def test_web_search_response_mapping(self) -> None:
        adapter = create_searchapi_adapter("test-key")
        mock_data = {
            "organic_results": [
                {
                    "title": "Python.org",
                    "link": "https://www.python.org",
                    "snippet": "Official site",
                    "displayed_link": "www.python.org",
                },
            ],
            "search_information": {"total_results": 1000000, "time_taken_displayed": "0.5"},
            "related_searches": [{"query": "python tutorial"}],
            "people_also_ask": [
                {"question": "Is Python easy?", "snippet": "Yes", "title": "Learning", "link": "https://ex.com"},
            ],
            "knowledge_graph": {
                "title": "Python",
                "type": "Language",
                "description": "A lang",
                "source": {"name": "Wikipedia", "link": "https://wiki.org"},
                "image": "https://ex.com/img.png",
            },
            "answer_box": {"snippet": "Python is great", "title": "Python", "link": "https://python.org"},
        }
        with _make_get_ctx("_searchapi", _mock_response(mock_data)):
            result = await adapter.search({"query": "python"})

        assert result["provider"] == "searchapi"
        assert result["totalResults"] == 1000000
        assert result["searchTime"] == 500.0
        assert result["knowledgePanel"]["source"] == "Wikipedia"
        assert result["knowledgePanel"]["sourceUrl"] == "https://wiki.org"
        assert result["knowledgePanel"]["imageUrl"] == "https://ex.com/img.png"
        assert result["answerBox"]["snippet"] == "Python is great"

    @pytest.mark.asyncio
    async def test_image_search(self) -> None:
        adapter = create_searchapi_adapter("test-key")
        mock_data = {
            "images": [
                {
                    "title": "Img",
                    "link": "https://ex.com",
                    "original": "https://ex.com/full.png",
                    "original_width": 1920,
                    "original_height": 1080,
                    "thumbnail": "https://ex.com/thumb.png",
                    "source": "example.com",
                },
            ],
        }
        with _make_get_ctx("_searchapi", _mock_response(mock_data)):
            result = await adapter.search({"query": "img", "type": "images"})

        r = result["results"][0]
        assert r["imageUrl"] == "https://ex.com/full.png"
        assert r["imageWidth"] == 1920
        assert r["source"] == "example.com"

    @pytest.mark.asyncio
    async def test_news_search_dict_source(self) -> None:
        adapter = create_searchapi_adapter("test-key")
        mock_data = {
            "news_results": [
                {"title": "News", "link": "https://ex.com", "snippet": "Breaking", "source": {"name": "CNN"}, "date": "2024-06-01"},
            ],
        }
        with _make_get_ctx("_searchapi", _mock_response(mock_data)):
            result = await adapter.search({"query": "news", "type": "news"})

        assert result["results"][0]["source"] == "CNN"

    @pytest.mark.asyncio
    async def test_video_search(self) -> None:
        adapter = create_searchapi_adapter("test-key")
        mock_data = {
            "video_results": [
                {
                    "title": "Vid",
                    "link": "https://yt.com",
                    "snippet": "A video",
                    "duration": "10:00",
                    "channel": {"name": "MyChan"},
                    "thumbnail": "https://ex.com/vthumb.png",
                    "date": "2024-01-01",
                },
            ],
        }
        with _make_get_ctx("_searchapi", _mock_response(mock_data)):
            result = await adapter.search({"query": "vid", "type": "videos"})

        r = result["results"][0]
        assert r["duration"] == "10:00"
        assert r["channel"] == "MyChan"

    @pytest.mark.asyncio
    async def test_request_params(self) -> None:
        adapter = create_searchapi_adapter("test-key")
        with _make_get_ctx("_searchapi", _mock_response({"organic_results": []})) as client:
            await adapter.search({
                "query": "test",
                "num": 10,
                "page": 2,
                "country": "us",
                "language": "en",
                "safe": True,
                "dateRange": "year",
            })
            params = client.get.call_args[1]["params"]
            assert params["engine"] == "google"
            assert params["q"] == "test"
            assert params["num"] == "10"
            assert params["page"] == "2"
            assert params["gl"] == "us"
            assert params["hl"] == "en"
            assert params["safe"] == "active"
            assert params["time_period"] == "last_year"

    @pytest.mark.asyncio
    async def test_ai_overview_with_include_flag(self) -> None:
        adapter = create_searchapi_adapter("test-key")
        search_data = {
            "organic_results": [],
            "ai_overview": {"page_token": "abc123"},
        }
        ai_data = {
            "markdown": "# AI\nPython.",
            "text_blocks": [
                {"type": "paragraph", "answer": "Python is great.", "answer_highlight": "great", "reference_indexes": [1]},
                {"type": "ordered_list", "items": [{"type": "paragraph", "answer": "Easy"}]},
                {"type": "code_blocks", "language": "python", "code": "print('hi')"},
                {"type": "video", "title": "Vid", "link": "https://yt.com", "duration": "5:00", "source": "YouTube", "channel": "Ch"},
            ],
            "reference_links": [
                {"index": 1, "title": "Ref", "link": "https://ref.com", "snippet": "A ref", "date": "2024-01-01", "source": "ref.com", "thumbnail": "https://ex.com/t.png"},
            ],
        }
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _mock_response(search_data if call_count == 1 else ai_data)

        with _make_get_ctx("_searchapi", _mock_response({})) as client:
            client.get.side_effect = mock_get
            result = await adapter.search({"query": "python", "includeAiOverview": True})

        ai = result["aiOverview"]
        assert ai["markdown"] == "# AI\nPython."
        assert ai["pageToken"] == "abc123"
        assert ai["textBlocks"][0]["answerHighlight"] == "great"
        assert ai["textBlocks"][1]["items"][0]["answer"] == "Easy"
        assert ai["textBlocks"][2]["language"] == "python"
        assert ai["textBlocks"][2]["code"] == "print('hi')"
        assert ai["textBlocks"][3]["video"]["channel"] == "Ch"
        assert ai["references"][0]["url"] == "https://ref.com"

    @pytest.mark.asyncio
    async def test_ai_overview_token_only_without_include_flag(self) -> None:
        adapter = create_searchapi_adapter("test-key")
        with _make_get_ctx("_searchapi", _mock_response({"organic_results": [], "ai_overview": {"page_token": "xyz"}})):
            result = await adapter.search({"query": "python"})
        assert result["aiOverview"]["pageToken"] == "xyz"
        assert result["aiOverview"]["textBlocks"] == []

    @pytest.mark.asyncio
    async def test_no_ai_overview_when_no_token(self) -> None:
        adapter = create_searchapi_adapter("test-key")
        with _make_get_ctx("_searchapi", _mock_response({"organic_results": []})):
            result = await adapter.search({"query": "python"})
        assert "aiOverview" not in result

    @pytest.mark.asyncio
    async def test_ai_overview_fetch_failure_graceful(self) -> None:
        adapter = create_searchapi_adapter("test-key")
        search_data = {"organic_results": [], "ai_overview": {"page_token": "tok"}}
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_response(search_data)
            return _mock_response({"error": "Failed"}, 500)

        with _make_get_ctx("_searchapi", _mock_response({})) as client:
            client.get.side_effect = mock_get
            result = await adapter.search({"query": "python", "includeAiOverview": True})
        # Should not crash. Either no aiOverview or fallback.
        assert result["provider"] == "searchapi"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        adapter = create_searchapi_adapter("bad")
        with _make_get_ctx("_searchapi", _mock_response({"error": "Bad key"}, 401)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 401

    def test_name_and_supports_type(self) -> None:
        adapter = create_searchapi_adapter("k")
        assert adapter.name == "searchapi"
        assert adapter.supports_type("web") is True


# ── ValueSERP ────────────────────────────────────────────────────────────────


class TestValueSerpAdapter:
    @pytest.mark.asyncio
    async def test_web_search_response_mapping(self) -> None:
        adapter = create_valueserp_adapter("test-key")
        mock_data = {
            "organic_results": [
                {
                    "title": "Python.org",
                    "link": "https://www.python.org",
                    "snippet": "Official site",
                    "domain": "python.org",
                    "date": "2024-01-01",
                },
            ],
            "search_information": {"total_results": 500000, "time_taken_displayed": "0.3"},
            "related_searches": [{"query": "python docs"}],
            "people_also_ask": [
                {"question": "What is Python?", "snippet": "A lang", "title": "Python", "link": "https://ex.com"},
            ],
            "knowledge_graph": {
                "title": "Python",
                "type": "Language",
                "description": "A lang",
                "source": {"name": "Wiki", "link": "https://wiki.org"},
                "image": "https://ex.com/img.png",
            },
            "answer_box": {"answer": "42", "title": "Answer", "link": "https://ex.com"},
        }
        with _make_get_ctx("_valueserp", _mock_response(mock_data)):
            result = await adapter.search({"query": "python"})

        assert result["provider"] == "valueserp"
        assert result["totalResults"] == 500000
        assert result["searchTime"] == 300.0
        assert result["results"][0]["domain"] == "python.org"
        assert result["relatedSearches"] == ["python docs"]
        assert result["knowledgePanel"]["source"] == "Wiki"
        assert result["answerBox"]["snippet"] == "42"

    @pytest.mark.asyncio
    async def test_image_search(self) -> None:
        adapter = create_valueserp_adapter("test-key")
        mock_data = {
            "image_results": [
                {
                    "title": "Img",
                    "link": "https://ex.com",
                    "original": "https://ex.com/full.png",
                    "original_width": 1024,
                    "original_height": 768,
                    "thumbnail": "https://ex.com/thumb.png",
                    "source": "example.com",
                },
            ],
        }
        with _make_get_ctx("_valueserp", _mock_response(mock_data)):
            result = await adapter.search({"query": "img", "type": "images"})

        r = result["results"][0]
        assert r["imageUrl"] == "https://ex.com/full.png"
        assert r["imageWidth"] == 1024

    @pytest.mark.asyncio
    async def test_news_search(self) -> None:
        adapter = create_valueserp_adapter("test-key")
        mock_data = {
            "news_results": [
                {"title": "News", "link": "https://ex.com", "snippet": "Breaking", "source": "BBC", "date": "2024-06-01", "thumbnail": "https://ex.com/t.png"},
            ],
        }
        with _make_get_ctx("_valueserp", _mock_response(mock_data)):
            result = await adapter.search({"query": "news", "type": "news"})

        r = result["results"][0]
        assert r["source"] == "BBC"
        assert r["thumbnail"] == "https://ex.com/t.png"

    @pytest.mark.asyncio
    async def test_video_search(self) -> None:
        adapter = create_valueserp_adapter("test-key")
        mock_data = {
            "video_results": [
                {"title": "Vid", "link": "https://yt.com", "snippet": "A video", "duration": "8:00", "channel": "MyCh", "thumbnail": "https://ex.com/vt.png", "date": "2024-01-01"},
            ],
        }
        with _make_get_ctx("_valueserp", _mock_response(mock_data)):
            result = await adapter.search({"query": "vid", "type": "videos"})

        r = result["results"][0]
        assert r["duration"] == "8:00"
        assert r["channel"] == "MyCh"

    @pytest.mark.asyncio
    async def test_request_params(self) -> None:
        adapter = create_valueserp_adapter("test-key")
        with _make_get_ctx("_valueserp", _mock_response({"organic_results": []})) as client:
            await adapter.search({
                "query": "test",
                "num": 15,
                "page": 3,
                "country": "gb",
                "language": "en",
                "safe": True,
                "dateRange": "month",
            })
            params = client.get.call_args[1]["params"]
            assert params["q"] == "test"
            assert params["search_type"] == "web"
            assert params["num"] == "15"
            assert params["page"] == "3"
            assert params["gl"] == "gb"
            assert params["hl"] == "en"
            assert params["safe"] == "active"
            assert params["time_period"] == "last_month"
            assert params["api_key"] == "test-key"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        adapter = create_valueserp_adapter("bad")
        with _make_get_ctx("_valueserp", _mock_response({"error": "Bad"}, 403)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 403

    def test_name_and_supports_type(self) -> None:
        adapter = create_valueserp_adapter("k")
        assert adapter.name == "valueserp"
        assert adapter.supports_type("web") is True
        assert adapter.supports_type("videos") is True


# ── ScrapingDog ──────────────────────────────────────────────────────────────


class TestScrapingDogAdapter:
    @pytest.mark.asyncio
    async def test_web_search_dict_response(self) -> None:
        adapter = create_scrapingdog_adapter("test-key")
        mock_data = {
            "organic_results": [
                {
                    "title": "Python.org",
                    "link": "https://www.python.org",
                    "snippet": "Official site",
                    "displayed_link": "python.org",
                    "date": "2024-01-01",
                },
            ],
            "people_also_ask": [
                {"question": "What is Python?", "snippet": "A lang", "title": "Python", "link": "https://ex.com"},
            ],
        }
        with _make_get_ctx("_scrapingdog", _mock_response(mock_data)):
            result = await adapter.search({"query": "python"})

        assert result["provider"] == "scrapingdog"
        assert result["results"][0]["domain"] == "python.org"
        assert result["results"][0]["datePublished"] == "2024-01-01"
        assert result["peopleAlsoAsk"][0]["question"] == "What is Python?"

    @pytest.mark.asyncio
    async def test_web_search_list_response(self) -> None:
        """ScrapingDog sometimes returns a raw list instead of dict."""
        adapter = create_scrapingdog_adapter("test-key")
        mock_data = [
            {"title": "Result 1", "link": "https://ex.com", "snippet": "A result", "domain": "ex.com"},
        ]
        with _make_get_ctx("_scrapingdog", _mock_response(mock_data)):
            result = await adapter.search({"query": "test"})

        assert len(result["results"]) == 1
        assert result["results"][0]["domain"] == "ex.com"

    @pytest.mark.asyncio
    async def test_image_search(self) -> None:
        adapter = create_scrapingdog_adapter("test-key")
        mock_data = {
            "image_results": [
                {
                    "title": "Img",
                    "link": "https://ex.com",
                    "original": "https://ex.com/full.png",
                    "original_width": 640,
                    "original_height": 480,
                    "thumbnail": "https://ex.com/t.png",
                    "source": "example.com",
                },
            ],
        }
        with _make_get_ctx("_scrapingdog", _mock_response(mock_data)):
            result = await adapter.search({"query": "img", "type": "images"})

        r = result["results"][0]
        assert r["imageUrl"] == "https://ex.com/full.png"
        assert r["imageWidth"] == 640

    @pytest.mark.asyncio
    async def test_news_search(self) -> None:
        adapter = create_scrapingdog_adapter("test-key")
        mock_data = {
            "news_results": [
                {"title": "News", "link": "https://ex.com", "snippet": "Breaking", "source": "BBC", "date": "2024-01-01", "thumbnail": "https://ex.com/t.png"},
            ],
        }
        with _make_get_ctx("_scrapingdog", _mock_response(mock_data)):
            result = await adapter.search({"query": "news", "type": "news"})

        r = result["results"][0]
        assert r["source"] == "BBC"
        assert r["thumbnail"] == "https://ex.com/t.png"

    @pytest.mark.asyncio
    async def test_request_params(self) -> None:
        adapter = create_scrapingdog_adapter("test-key")
        with _make_get_ctx("_scrapingdog", _mock_response({"organic_results": []})) as client:
            await adapter.search({
                "query": "test",
                "num": 10,
                "page": 3,
                "country": "us",
                "language": "en",
            })
            params = client.get.call_args[1]["params"]
            assert params["query"] == "test"
            assert params["results"] == "10"
            assert params["page"] == "2"  # 0-indexed
            assert params["country"] == "us"
            assert params["language"] == "en"
            assert params["api_key"] == "test-key"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        adapter = create_scrapingdog_adapter("bad")
        with _make_get_ctx("_scrapingdog", _mock_response({"error": "Auth failed"}, 401)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 401

    def test_supports_type(self) -> None:
        adapter = create_scrapingdog_adapter("k")
        assert adapter.supports_type("web") is True
        assert adapter.supports_type("images") is True
        assert adapter.supports_type("news") is True
        assert adapter.supports_type("videos") is False

    def test_name(self) -> None:
        adapter = create_scrapingdog_adapter("k")
        assert adapter.name == "scrapingdog"


# ── BrightData ───────────────────────────────────────────────────────────────


class TestBrightDataAdapter:
    @pytest.mark.asyncio
    async def test_web_search_response_mapping(self) -> None:
        adapter = create_brightdata_adapter("test-key")
        mock_data = {
            "organic": [
                {
                    "title": "Python.org",
                    "link": "https://www.python.org",
                    "description": "Official site",
                    "display_link": "python.org",
                },
            ],
            "knowledge_panel": {
                "title": "Python",
                "type": "Language",
                "description": "A lang",
                "image": "https://ex.com/img.png",
            },
            "people_also_ask": [
                {"question": "What is Python?", "snippet": "A lang", "link": "https://ex.com"},
            ],
            "related_searches": [{"query": "python docs"}, "raw string search"],
        }
        with _make_post_ctx("_brightdata", _mock_response(mock_data)):
            result = await adapter.search({"query": "python"})

        assert result["provider"] == "brightdata"
        assert result["results"][0]["domain"] == "python.org"
        assert result["knowledgePanel"]["imageUrl"] == "https://ex.com/img.png"
        assert result["peopleAlsoAsk"][0]["url"] == "https://ex.com"
        assert result["relatedSearches"] == ["python docs", "raw string search"]

    @pytest.mark.asyncio
    async def test_image_search(self) -> None:
        adapter = create_brightdata_adapter("test-key")
        mock_data = {
            "organic": [
                {
                    "title": "Img",
                    "link": "https://ex.com/img.png",
                    "description": "An image",
                    "thumbnail": "https://ex.com/t.png",
                    "display_link": "example.com",
                },
            ],
        }
        with _make_post_ctx("_brightdata", _mock_response(mock_data)):
            result = await adapter.search({"query": "img", "type": "images"})

        r = result["results"][0]
        assert r["imageUrl"] == "https://ex.com/img.png"
        assert r["thumbnail"] == "https://ex.com/t.png"
        assert r["source"] == "example.com"

    @pytest.mark.asyncio
    async def test_news_search(self) -> None:
        adapter = create_brightdata_adapter("test-key")
        mock_data = {
            "organic": [
                {"title": "News", "link": "https://ex.com", "description": "Breaking", "display_link": "bbc.com", "date": "2024-06-01"},
            ],
        }
        with _make_post_ctx("_brightdata", _mock_response(mock_data)):
            result = await adapter.search({"query": "news", "type": "news"})

        r = result["results"][0]
        assert r["source"] == "bbc.com"
        assert r["datePublished"] == "2024-06-01"

    @pytest.mark.asyncio
    async def test_video_search(self) -> None:
        adapter = create_brightdata_adapter("test-key")
        mock_data = {
            "organic": [
                {"title": "Vid", "link": "https://yt.com", "description": "A vid", "thumbnail": "https://ex.com/t.png", "duration": "10:00"},
            ],
        }
        with _make_post_ctx("_brightdata", _mock_response(mock_data)):
            result = await adapter.search({"query": "vid", "type": "videos"})

        r = result["results"][0]
        assert r["thumbnail"] == "https://ex.com/t.png"
        assert r["duration"] == "10:00"

    @pytest.mark.asyncio
    async def test_search_url_construction(self) -> None:
        adapter = create_brightdata_adapter("test-key")
        with _make_post_ctx("_brightdata", _mock_response({"organic": []})) as client:
            await adapter.search({
                "query": "test query",
                "num": 20,
                "page": 2,
                "country": "gb",
                "language": "en",
                "safe": True,
                "type": "images",
            })
            body = client.post.call_args[1]["json"]
            url = body["url"]
            assert "q=test+query" in url
            assert "tbm=isch" in url
            assert "gl=gb" in url
            assert "hl=en" in url
            assert "num=20" in url
            assert "start=20" in url
            assert "safe=active" in url
            assert "brd_json=1" in url

    @pytest.mark.asyncio
    async def test_api_key_header(self) -> None:
        adapter = create_brightdata_adapter("my-bd-key")
        with _make_post_ctx("_brightdata", _mock_response({"organic": []})) as client:
            await adapter.search({"query": "test"})
            headers = client.post.call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer my-bd-key"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        adapter = create_brightdata_adapter("bad")
        with _make_post_ctx("_brightdata", _mock_response({"message": "Forbidden"}, 403)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 403

    def test_name_and_supports_type(self) -> None:
        adapter = create_brightdata_adapter("k")
        assert adapter.name == "brightdata"
        assert adapter.supports_type("web") is True
        assert adapter.supports_type("videos") is True


# ── SearchCans ───────────────────────────────────────────────────────────────


class TestSearchCansAdapter:
    @pytest.mark.asyncio
    async def test_web_search_response_mapping(self) -> None:
        adapter = create_searchcans_adapter("test-key")
        mock_data = {
            "organic_results": [
                {
                    "title": "Python.org",
                    "link": "https://www.python.org",
                    "snippet": "Official site",
                    "displayed_link": "python.org",
                    "date": "2024-01-01",
                },
            ],
            "people_also_ask": [
                {"question": "What is Python?", "snippet": "A lang", "link": "https://ex.com"},
            ],
            "knowledge_panel": {
                "title": "Python",
                "type": "Language",
                "description": "A lang",
            },
        }
        with _make_post_ctx("_searchcans", _mock_response(mock_data)):
            result = await adapter.search({"query": "python"})

        assert result["provider"] == "searchcans"
        assert result["results"][0]["domain"] == "python.org"
        assert result["results"][0]["datePublished"] == "2024-01-01"
        assert result["peopleAlsoAsk"][0]["question"] == "What is Python?"
        assert result["knowledgePanel"]["title"] == "Python"
        assert result["knowledgePanel"]["type"] == "Language"

    @pytest.mark.asyncio
    async def test_fallback_to_results_key(self) -> None:
        """SearchCans may return 'results' instead of 'organic_results'."""
        adapter = create_searchcans_adapter("test-key")
        mock_data = {
            "results": [
                {"title": "Result 1", "url": "https://ex.com", "description": "A result", "domain": "ex.com"},
            ],
        }
        with _make_post_ctx("_searchcans", _mock_response(mock_data)):
            result = await adapter.search({"query": "test"})

        assert len(result["results"]) == 1
        assert result["results"][0]["url"] == "https://ex.com"

    @pytest.mark.asyncio
    async def test_request_body(self) -> None:
        adapter = create_searchcans_adapter("test-key")
        with _make_post_ctx("_searchcans", _mock_response({"organic_results": []})) as client:
            await adapter.search({
                "query": "test",
                "page": 3,
                "country": "us",
                "language": "en",
            })
            body = client.post.call_args[1]["json"]
            assert body["s"] == "test"
            assert body["t"] == "google"
            assert body["p"] == 3
            assert body["gl"] == "us"
            assert body["hl"] == "en"

    @pytest.mark.asyncio
    async def test_api_key_header(self) -> None:
        adapter = create_searchcans_adapter("my-sc-key")
        with _make_post_ctx("_searchcans", _mock_response({"organic_results": []})) as client:
            await adapter.search({"query": "test"})
            headers = client.post.call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer my-sc-key"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        adapter = create_searchcans_adapter("bad")
        with _make_post_ctx("_searchcans", _mock_response({"error": "Bad key"}, 401)):
            with pytest.raises(AnySerpError) as exc_info:
                await adapter.search({"query": "test"})
            assert exc_info.value.code == 401

    def test_supports_type(self) -> None:
        adapter = create_searchcans_adapter("k")
        assert adapter.supports_type("web") is True
        assert adapter.supports_type("news") is True
        assert adapter.supports_type("images") is False
        assert adapter.supports_type("videos") is False

    def test_name(self) -> None:
        adapter = create_searchcans_adapter("k")
        assert adapter.name == "searchcans"


# ── Unified format validation ────────────────────────────────────────────────


class TestUnifiedResponseFormat:
    """Verify all providers return the same top-level shape."""

    REQUIRED_KEYS = {"provider", "query", "results"}

    @pytest.mark.asyncio
    async def test_serper_unified_format(self) -> None:
        adapter = create_serper_adapter("k")
        with _make_post_ctx("_serper", _mock_response({"organic": []})):
            result = await adapter.search({"query": "test"})
        assert self.REQUIRED_KEYS <= set(result.keys())
        assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_serpapi_unified_format(self) -> None:
        adapter = create_serpapi_adapter("k")
        with _make_get_ctx("_serpapi", _mock_response({"organic_results": []})):
            result = await adapter.search({"query": "test"})
        assert self.REQUIRED_KEYS <= set(result.keys())

    @pytest.mark.asyncio
    async def test_google_unified_format(self) -> None:
        adapter = create_google_adapter("k", "e")
        with _make_get_ctx("_google", _mock_response({"items": []})):
            result = await adapter.search({"query": "test"})
        assert self.REQUIRED_KEYS <= set(result.keys())

    @pytest.mark.asyncio
    async def test_bing_unified_format(self) -> None:
        adapter = create_bing_adapter("k")
        with _make_get_ctx("_bing", _mock_response({"webPages": {"value": []}})):
            result = await adapter.search({"query": "test"})
        assert self.REQUIRED_KEYS <= set(result.keys())

    @pytest.mark.asyncio
    async def test_brave_unified_format(self) -> None:
        adapter = create_brave_adapter("k")
        with _make_get_ctx("_brave", _mock_response({"web": {"results": []}})):
            result = await adapter.search({"query": "test"})
        assert self.REQUIRED_KEYS <= set(result.keys())

    @pytest.mark.asyncio
    async def test_dataforseo_unified_format(self) -> None:
        adapter = create_dataforseo_adapter("u", "p")
        mock_data = {
            "status_code": 20000,
            "tasks": [{"status_code": 20000, "result": [{"items": []}]}],
        }
        with _make_post_ctx("_dataforseo", _mock_response(mock_data)):
            result = await adapter.search({"query": "test"})
        assert self.REQUIRED_KEYS <= set(result.keys())

    @pytest.mark.asyncio
    async def test_searchapi_unified_format(self) -> None:
        adapter = create_searchapi_adapter("k")
        with _make_get_ctx("_searchapi", _mock_response({"organic_results": []})):
            result = await adapter.search({"query": "test"})
        assert self.REQUIRED_KEYS <= set(result.keys())

    @pytest.mark.asyncio
    async def test_valueserp_unified_format(self) -> None:
        adapter = create_valueserp_adapter("k")
        with _make_get_ctx("_valueserp", _mock_response({"organic_results": []})):
            result = await adapter.search({"query": "test"})
        assert self.REQUIRED_KEYS <= set(result.keys())

    @pytest.mark.asyncio
    async def test_scrapingdog_unified_format(self) -> None:
        adapter = create_scrapingdog_adapter("k")
        with _make_get_ctx("_scrapingdog", _mock_response({"organic_results": []})):
            result = await adapter.search({"query": "test"})
        assert self.REQUIRED_KEYS <= set(result.keys())

    @pytest.mark.asyncio
    async def test_brightdata_unified_format(self) -> None:
        adapter = create_brightdata_adapter("k")
        with _make_post_ctx("_brightdata", _mock_response({"organic": []})):
            result = await adapter.search({"query": "test"})
        assert self.REQUIRED_KEYS <= set(result.keys())

    @pytest.mark.asyncio
    async def test_searchcans_unified_format(self) -> None:
        adapter = create_searchcans_adapter("k")
        with _make_post_ctx("_searchcans", _mock_response({"organic_results": []})):
            result = await adapter.search({"query": "test"})
        assert self.REQUIRED_KEYS <= set(result.keys())
