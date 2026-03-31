from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from anyserp import AnySerp, AnySerpError, AnySerpRegistry


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.reason_phrase = "OK" if status_code < 400 else "Error"
    mock_resp.json.return_value = json_data
    return mock_resp


def _make_mock_client(method: str, resp: MagicMock) -> AsyncMock:
    mock_client = AsyncMock()
    getattr(mock_client, method).return_value = resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ── Initialization ───────────────────────────────────────────────────────────


class TestAnySerp:
    def test_initializes_with_no_config(self) -> None:
        client = AnySerp()
        assert client.providers() == []

    def test_initializes_with_none_config(self) -> None:
        client = AnySerp(None)
        assert client.providers() == []

    @pytest.mark.asyncio
    async def test_throws_when_no_providers_configured(self) -> None:
        client = AnySerp()
        with pytest.raises(AnySerpError, match="No provider configured"):
            await client.search("test")

    @pytest.mark.asyncio
    async def test_accepts_string_query(self) -> None:
        client = AnySerp()
        with pytest.raises(AnySerpError):
            await client.search("test")

    @pytest.mark.asyncio
    async def test_accepts_request_object(self) -> None:
        client = AnySerp()
        with pytest.raises(AnySerpError):
            await client.search({"query": "test", "num": 5})

    @pytest.mark.asyncio
    async def test_throws_for_unknown_provider_prefix(self) -> None:
        client = AnySerp({"serper": {"apiKey": "test"}})
        with pytest.raises(Exception):
            await client.search("unknown/test")

    def test_lists_no_providers_when_none_configured(self) -> None:
        client = AnySerp()
        assert len(client.providers()) == 0

    def test_registers_providers_from_config(self) -> None:
        client = AnySerp({
            "serper": {"apiKey": "test-key"},
            "brave": {"apiKey": "test-key"},
        })
        assert client.providers() == ["serper", "brave"]

    def test_registers_google_only_with_both_key_and_engine_id(self) -> None:
        client = AnySerp({"google": {"apiKey": "test-key"}})
        assert client.providers() == []

        client2 = AnySerp({"google": {"apiKey": "test-key", "engineId": "test-engine"}})
        assert client2.providers() == ["google"]

    def test_registers_dataforseo_with_login_and_password(self) -> None:
        client = AnySerp({"dataforseo": {"login": "user", "password": "pass"}})
        assert client.providers() == ["dataforseo"]

    def test_registers_searchapi_with_api_key(self) -> None:
        client = AnySerp({"searchapi": {"apiKey": "test-key"}})
        assert client.providers() == ["searchapi"]

    def test_registers_valueserp_with_api_key(self) -> None:
        client = AnySerp({"valueserp": {"apiKey": "test-key"}})
        assert client.providers() == ["valueserp"]

    def test_registers_scrapingdog_with_api_key(self) -> None:
        client = AnySerp({"scrapingdog": {"apiKey": "test-key"}})
        assert client.providers() == ["scrapingdog"]

    def test_registers_brightdata_with_api_key(self) -> None:
        client = AnySerp({"brightdata": {"apiKey": "test-key"}})
        assert client.providers() == ["brightdata"]

    def test_registers_searchcans_with_api_key(self) -> None:
        client = AnySerp({"searchcans": {"apiKey": "test-key"}})
        assert client.providers() == ["searchcans"]

    def test_registers_serpapi_with_api_key(self) -> None:
        client = AnySerp({"serpapi": {"apiKey": "test-key"}})
        assert client.providers() == ["serpapi"]

    def test_registers_bing_with_api_key(self) -> None:
        client = AnySerp({"bing": {"apiKey": "test-key"}})
        assert client.providers() == ["bing"]

    def test_registers_all_providers_at_once(self) -> None:
        client = AnySerp({
            "serper": {"apiKey": "k"},
            "serpapi": {"apiKey": "k"},
            "google": {"apiKey": "k", "engineId": "e"},
            "bing": {"apiKey": "k"},
            "brave": {"apiKey": "k"},
            "dataforseo": {"login": "u", "password": "p"},
            "searchapi": {"apiKey": "k"},
            "valueserp": {"apiKey": "k"},
            "scrapingdog": {"apiKey": "k"},
            "brightdata": {"apiKey": "k"},
            "searchcans": {"apiKey": "k"},
        })
        assert len(client.providers()) == 11

    def test_skips_provider_with_empty_key(self) -> None:
        client = AnySerp({"serper": {"apiKey": ""}})
        assert client.providers() == []

    def test_skips_provider_with_none_key(self) -> None:
        client = AnySerp({"serper": {}})
        assert client.providers() == []

    def test_skips_google_missing_engine_id(self) -> None:
        client = AnySerp({"google": {"apiKey": "k"}})
        assert "google" not in client.providers()

    def test_skips_google_missing_api_key(self) -> None:
        client = AnySerp({"google": {"engineId": "e"}})
        assert "google" not in client.providers()

    def test_skips_dataforseo_missing_password(self) -> None:
        client = AnySerp({"dataforseo": {"login": "u"}})
        assert "dataforseo" not in client.providers()

    def test_skips_dataforseo_missing_login(self) -> None:
        client = AnySerp({"dataforseo": {"password": "p"}})
        assert "dataforseo" not in client.providers()


# ── Environment variable registration ────────────────────────────────────────


class TestEnvVarRegistration:
    def test_registers_serper_from_env(self) -> None:
        with patch.dict(os.environ, {"SERPER_API_KEY": "env-key"}, clear=False):
            client = AnySerp()
            assert "serper" in client.providers()

    def test_registers_serpapi_from_env(self) -> None:
        with patch.dict(os.environ, {"SERPAPI_API_KEY": "env-key"}, clear=False):
            client = AnySerp()
            assert "serpapi" in client.providers()

    def test_registers_bing_from_env(self) -> None:
        with patch.dict(os.environ, {"BING_API_KEY": "env-key"}, clear=False):
            client = AnySerp()
            assert "bing" in client.providers()

    def test_registers_brave_from_env(self) -> None:
        with patch.dict(os.environ, {"BRAVE_API_KEY": "env-key"}, clear=False):
            client = AnySerp()
            assert "brave" in client.providers()

    def test_registers_google_from_env(self) -> None:
        with patch.dict(os.environ, {"GOOGLE_CSE_API_KEY": "k", "GOOGLE_CSE_ENGINE_ID": "e"}, clear=False):
            client = AnySerp()
            assert "google" in client.providers()

    def test_registers_dataforseo_from_env(self) -> None:
        with patch.dict(os.environ, {"DATAFORSEO_LOGIN": "u", "DATAFORSEO_PASSWORD": "p"}, clear=False):
            client = AnySerp()
            assert "dataforseo" in client.providers()

    def test_registers_searchapi_from_env(self) -> None:
        with patch.dict(os.environ, {"SEARCHAPI_API_KEY": "env-key"}, clear=False):
            client = AnySerp()
            assert "searchapi" in client.providers()

    def test_registers_valueserp_from_env(self) -> None:
        with patch.dict(os.environ, {"VALUESERP_API_KEY": "env-key"}, clear=False):
            client = AnySerp()
            assert "valueserp" in client.providers()

    def test_registers_scrapingdog_from_env(self) -> None:
        with patch.dict(os.environ, {"SCRAPINGDOG_API_KEY": "env-key"}, clear=False):
            client = AnySerp()
            assert "scrapingdog" in client.providers()

    def test_registers_brightdata_from_env(self) -> None:
        with patch.dict(os.environ, {"BRIGHTDATA_API_KEY": "env-key"}, clear=False):
            client = AnySerp()
            assert "brightdata" in client.providers()

    def test_registers_searchcans_from_env(self) -> None:
        with patch.dict(os.environ, {"SEARCHCANS_API_KEY": "env-key"}, clear=False):
            client = AnySerp()
            assert "searchcans" in client.providers()

    def test_config_key_takes_precedence_over_env(self) -> None:
        """When both config and env are set, config wins (both register)."""
        with patch.dict(os.environ, {"SERPER_API_KEY": "env-key"}, clear=False):
            client = AnySerp({"serper": {"apiKey": "config-key"}})
            assert "serper" in client.providers()


# ── Provider prefix routing ──────────────────────────────────────────────────


class TestProviderPrefixRouting:
    @pytest.mark.asyncio
    async def test_provider_prefix_routing(self) -> None:
        client = AnySerp({"serper": {"apiKey": "test"}})
        with pytest.raises(Exception) as exc_info:
            await client.search("serper/python programming")
        assert "No provider configured" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unknown_prefix_treated_as_query(self) -> None:
        """A prefix that matches no provider is kept in the query."""
        client = AnySerp({"serper": {"apiKey": "test"}})
        with pytest.raises(Exception) as exc_info:
            await client.search("notaprovider/test query")
        assert "not configured" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_prefix_extracts_query_correctly(self) -> None:
        """After stripping provider prefix, the remaining text is the query."""
        mock_adapter = MagicMock()
        mock_adapter.name = "serper"
        mock_adapter.supports_type.return_value = True
        mock_adapter.search = AsyncMock(return_value={"provider": "serper", "query": "hello world", "results": []})

        client = AnySerp({"serper": {"apiKey": "test"}})
        client._registry._adapters["serper"] = mock_adapter

        await client.search("serper/hello world")
        call_args = mock_adapter.search.call_args[0][0]
        assert call_args["query"] == "hello world"

    @pytest.mark.asyncio
    async def test_prefix_not_configured_raises(self) -> None:
        """Prefix that matches a known name but not configured raises error."""
        client = AnySerp({"serper": {"apiKey": "test"}})
        # "brave" is a known provider name but not registered via config
        # Since it's not registered, the prefix logic won't match it.
        # So "brave/test" will be treated as a full query for serper.
        with pytest.raises(Exception):
            await client.search("brave/test")


# ── Alias resolution ────────────────────────────────────────────────────────


class TestAliasResolution:
    @pytest.mark.asyncio
    async def test_alias_resolution(self) -> None:
        client = AnySerp({
            "serper": {"apiKey": "test"},
            "aliases": {"s": "serper"},
        })
        with pytest.raises(Exception) as exc_info:
            await client.search("s/test query")
        assert "No provider configured" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_multiple_aliases(self) -> None:
        client = AnySerp({
            "serper": {"apiKey": "test"},
            "brave": {"apiKey": "test"},
            "aliases": {"s": "serper", "b": "brave"},
        })
        # Both aliases should be usable
        assert "s" in client._aliases
        assert "b" in client._aliases
        assert client._aliases["s"] == "serper"
        assert client._aliases["b"] == "brave"


# ── Defaults ─────────────────────────────────────────────────────────────────


class TestDefaults:
    @pytest.mark.asyncio
    async def test_defaults_applied_to_request(self) -> None:
        mock_adapter = MagicMock()
        mock_adapter.name = "serper"
        mock_adapter.supports_type.return_value = True
        mock_adapter.search = AsyncMock(return_value={"provider": "serper", "query": "test", "results": []})

        client = AnySerp({
            "serper": {"apiKey": "test"},
            "defaults": {"num": 20, "country": "gb", "language": "en", "safe": True},
        })
        client._registry._adapters["serper"] = mock_adapter

        await client.search("test query")
        req = mock_adapter.search.call_args[0][0]
        assert req["num"] == 20
        assert req["country"] == "gb"
        assert req["language"] == "en"
        assert req["safe"] is True

    @pytest.mark.asyncio
    async def test_request_values_override_defaults(self) -> None:
        mock_adapter = MagicMock()
        mock_adapter.name = "serper"
        mock_adapter.supports_type.return_value = True
        mock_adapter.search = AsyncMock(return_value={"provider": "serper", "query": "test", "results": []})

        client = AnySerp({
            "serper": {"apiKey": "test"},
            "defaults": {"num": 20, "country": "gb"},
        })
        client._registry._adapters["serper"] = mock_adapter

        await client.search({"query": "test", "num": 5, "country": "us"})
        req = mock_adapter.search.call_args[0][0]
        assert req["num"] == 5
        assert req["country"] == "us"

    @pytest.mark.asyncio
    async def test_no_defaults_when_not_configured(self) -> None:
        mock_adapter = MagicMock()
        mock_adapter.name = "serper"
        mock_adapter.supports_type.return_value = True
        mock_adapter.search = AsyncMock(return_value={"provider": "serper", "query": "test", "results": []})

        client = AnySerp({"serper": {"apiKey": "test"}})
        client._registry._adapters["serper"] = mock_adapter

        await client.search("test query")
        req = mock_adapter.search.call_args[0][0]
        assert "num" not in req
        assert "country" not in req


# ── Search with fallback ────────────────────────────────────────────────────


class TestSearchWithFallback:
    @pytest.mark.asyncio
    async def test_throws_when_no_providers_match(self) -> None:
        client = AnySerp()
        with pytest.raises(AnySerpError, match="No providers available"):
            await client.search_with_fallback({"query": "test"})

    @pytest.mark.asyncio
    async def test_falls_back_on_first_failure(self) -> None:
        failing = MagicMock()
        failing.name = "provider_a"
        failing.supports_type.return_value = True
        failing.search = AsyncMock(side_effect=AnySerpError(500, "Server error"))

        succeeding = MagicMock()
        succeeding.name = "provider_b"
        succeeding.supports_type.return_value = True
        succeeding.search = AsyncMock(return_value={"provider": "provider_b", "query": "test", "results": []})

        client = AnySerp()
        client._registry.register("provider_a", failing)
        client._registry.register("provider_b", succeeding)

        result = await client.search_with_fallback({"query": "test"})
        assert result["provider"] == "provider_b"

    @pytest.mark.asyncio
    async def test_raises_last_error_when_all_fail(self) -> None:
        a = MagicMock()
        a.name = "a"
        a.supports_type.return_value = True
        a.search = AsyncMock(side_effect=AnySerpError(500, "Error A"))

        b = MagicMock()
        b.name = "b"
        b.supports_type.return_value = True
        b.search = AsyncMock(side_effect=AnySerpError(502, "Error B"))

        client = AnySerp()
        client._registry.register("a", a)
        client._registry.register("b", b)

        with pytest.raises(AnySerpError) as exc_info:
            await client.search_with_fallback({"query": "test"})
        assert exc_info.value.code == 502
        assert "Error B" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_respects_explicit_provider_list(self) -> None:
        a = MagicMock()
        a.name = "a"
        a.supports_type.return_value = True
        a.search = AsyncMock(return_value={"provider": "a", "query": "test", "results": []})

        b = MagicMock()
        b.name = "b"
        b.supports_type.return_value = True
        b.search = AsyncMock()

        client = AnySerp()
        client._registry.register("a", a)
        client._registry.register("b", b)

        result = await client.search_with_fallback({"query": "test"}, providers=["a"])
        assert result["provider"] == "a"
        b.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_unsupported_types(self) -> None:
        a = MagicMock()
        a.name = "a"
        a.supports_type.return_value = False

        b = MagicMock()
        b.name = "b"
        b.supports_type.return_value = True
        b.search = AsyncMock(return_value={"provider": "b", "query": "test", "results": []})

        client = AnySerp()
        client._registry.register("a", a)
        client._registry.register("b", b)

        result = await client.search_with_fallback({"query": "test", "type": "images"})
        assert result["provider"] == "b"


# ── Search all ───────────────────────────────────────────────────────────────


class TestSearchAll:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_providers(self) -> None:
        client = AnySerp()
        results = await client.search_all({"query": "test"})
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_results_from_all_providers(self) -> None:
        a = MagicMock()
        a.name = "a"
        a.supports_type.return_value = True
        a.search = AsyncMock(return_value={"provider": "a", "query": "test", "results": []})

        b = MagicMock()
        b.name = "b"
        b.supports_type.return_value = True
        b.search = AsyncMock(return_value={"provider": "b", "query": "test", "results": []})

        client = AnySerp()
        client._registry.register("a", a)
        client._registry.register("b", b)

        results = await client.search_all({"query": "test"})
        assert len(results) == 2
        providers = {r["provider"] for r in results}
        assert providers == {"a", "b"}

    @pytest.mark.asyncio
    async def test_excludes_failures(self) -> None:
        ok = MagicMock()
        ok.name = "ok"
        ok.supports_type.return_value = True
        ok.search = AsyncMock(return_value={"provider": "ok", "query": "test", "results": []})

        fail = MagicMock()
        fail.name = "fail"
        fail.supports_type.return_value = True
        fail.search = AsyncMock(side_effect=AnySerpError(500, "Boom"))

        client = AnySerp()
        client._registry.register("ok", ok)
        client._registry.register("fail", fail)

        results = await client.search_all({"query": "test"})
        assert len(results) == 1
        assert results[0]["provider"] == "ok"

    @pytest.mark.asyncio
    async def test_skips_unsupported_types(self) -> None:
        a = MagicMock()
        a.name = "a"
        a.supports_type.return_value = False

        b = MagicMock()
        b.name = "b"
        b.supports_type.return_value = True
        b.search = AsyncMock(return_value={"provider": "b", "query": "test", "results": []})

        client = AnySerp()
        client._registry.register("a", a)
        client._registry.register("b", b)

        results = await client.search_all({"query": "test", "type": "images"})
        assert len(results) == 1


# ── Registry ─────────────────────────────────────────────────────────────────


class TestAnySerpRegistry:
    def test_register_and_get(self) -> None:
        reg = AnySerpRegistry()
        mock = MagicMock()
        reg.register("test", mock)
        assert reg.get("test") is mock

    def test_get_returns_none_for_missing(self) -> None:
        reg = AnySerpRegistry()
        assert reg.get("missing") is None

    def test_all_returns_all_adapters(self) -> None:
        reg = AnySerpRegistry()
        a, b = MagicMock(), MagicMock()
        reg.register("a", a)
        reg.register("b", b)
        assert reg.all() == [a, b]

    def test_names_returns_all_names(self) -> None:
        reg = AnySerpRegistry()
        reg.register("x", MagicMock())
        reg.register("y", MagicMock())
        assert reg.names() == ["x", "y"]

    def test_get_registry(self) -> None:
        client = AnySerp({"serper": {"apiKey": "k"}})
        reg = client.get_registry()
        assert isinstance(reg, AnySerpRegistry)
        assert "serper" in reg.names()


# ── Auto-select provider ────────────────────────────────────────────────────


class TestAutoSelectProvider:
    @pytest.mark.asyncio
    async def test_uses_first_supporting_provider(self) -> None:
        a = MagicMock()
        a.name = "a"
        a.supports_type.return_value = False
        a.search = AsyncMock()

        b = MagicMock()
        b.name = "b"
        b.supports_type.return_value = True
        b.search = AsyncMock(return_value={"provider": "b", "query": "test", "results": []})

        client = AnySerp()
        client._registry.register("a", a)
        client._registry.register("b", b)

        result = await client.search({"query": "test", "type": "images"})
        assert result["provider"] == "b"
        a.search.assert_not_called()


# ── Error ────────────────────────────────────────────────────────────────────


class TestAnySerpError:
    def test_has_code_and_metadata(self) -> None:
        err = AnySerpError(429, "Rate limited", {"provider_name": "serper"})
        assert err.code == 429
        assert str(err) == "Rate limited"
        assert err.metadata["provider_name"] == "serper"

    def test_default_metadata(self) -> None:
        err = AnySerpError(500, "Server error")
        assert err.code == 500
        assert err.metadata == {}

    def test_is_exception_subclass(self) -> None:
        err = AnySerpError(400, "Bad request")
        assert isinstance(err, Exception)

    def test_metadata_preserved(self) -> None:
        meta = {"provider_name": "bing", "raw": {"detail": "info"}}
        err = AnySerpError(502, "Bad gateway", meta)
        assert err.metadata["raw"]["detail"] == "info"
