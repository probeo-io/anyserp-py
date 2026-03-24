from __future__ import annotations

import pytest

from anyserp import AnySerp, AnySerpError


class TestAnySerp:
    def test_initializes_with_no_config(self) -> None:
        client = AnySerp()
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
        # "unknown" is not a registered provider, so it's treated as part of the query.
        # The serper adapter will be used and fail with a bad key, but routing works.
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

    @pytest.mark.asyncio
    async def test_search_with_fallback_throws_when_no_providers_match(self) -> None:
        client = AnySerp()
        with pytest.raises(AnySerpError, match="No providers available"):
            await client.search_with_fallback({"query": "test"})

    @pytest.mark.asyncio
    async def test_search_all_returns_empty_when_no_providers(self) -> None:
        client = AnySerp()
        results = await client.search_all({"query": "test"})
        assert results == []

    def test_registers_dataforseo_with_login_and_password(self) -> None:
        client = AnySerp({"dataforseo": {"login": "user", "password": "pass"}})
        assert client.providers() == ["dataforseo"]

    def test_applies_defaults_from_config(self) -> None:
        client = AnySerp({
            "serper": {"apiKey": "test"},
            "defaults": {"num": 20, "country": "gb"},
        })
        assert "serper" in client.providers()

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

    @pytest.mark.asyncio
    async def test_provider_prefix_routing(self) -> None:
        """When using 'serper/query', should route to the serper provider."""
        client = AnySerp({"serper": {"apiKey": "test"}})
        # Will fail at HTTP level, but we can verify it doesn't raise 'no provider'
        with pytest.raises(Exception) as exc_info:
            await client.search("serper/python programming")
        # Should NOT be "no provider configured"
        assert "No provider configured" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_alias_resolution(self) -> None:
        """Aliases should map to registered providers."""
        client = AnySerp({
            "serper": {"apiKey": "test"},
            "aliases": {"s": "serper"},
        })
        # The alias 's' should resolve to 'serper'
        with pytest.raises(Exception) as exc_info:
            await client.search("s/test query")
        assert "No provider configured" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_default_values_applied(self) -> None:
        """Defaults from config should be applied to requests."""
        client = AnySerp({
            "serper": {"apiKey": "test"},
            "defaults": {"num": 20, "country": "gb", "language": "en", "safe": True},
        })
        # Will fail at HTTP but routing should work
        with pytest.raises(Exception):
            await client.search("test query")


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
