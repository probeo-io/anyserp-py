from __future__ import annotations

import asyncio
import os
from typing import Any

from ._errors import AnySerpError
from ._types import AnySerpConfig, SearchAdapter
from .providers._serper import create_serper_adapter
from .providers._serpapi import create_serpapi_adapter
from .providers._google import create_google_adapter
from .providers._bing import create_bing_adapter
from .providers._brave import create_brave_adapter
from .providers._dataforseo import create_dataforseo_adapter
from .providers._searchapi import create_searchapi_adapter
from .providers._valueserp import create_valueserp_adapter
from .providers._scrapingdog import create_scrapingdog_adapter
from .providers._brightdata import create_brightdata_adapter
from .providers._searchcans import create_searchcans_adapter


class AnySerpRegistry:
    """Registry of search provider adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, SearchAdapter] = {}

    def register(self, name: str, adapter: SearchAdapter) -> None:
        self._adapters[name] = adapter

    def get(self, name: str) -> SearchAdapter | None:
        return self._adapters.get(name)

    def all(self) -> list[SearchAdapter]:
        return list(self._adapters.values())

    def names(self) -> list[str]:
        return list(self._adapters.keys())


class AnySerp:
    """Unified SERP API router supporting 11 providers."""

    def __init__(self, config: AnySerpConfig | None = None) -> None:
        self._config: AnySerpConfig = config or {}
        self._registry = AnySerpRegistry()
        self._aliases: dict[str, str] = dict(self._config.get("aliases", {}))
        self._register_providers()

    def _register_providers(self) -> None:
        cfg = self._config

        # Serper
        serper_key = (cfg.get("serper") or {}).get("apiKey") or os.environ.get("SERPER_API_KEY")
        if serper_key:
            self._registry.register("serper", create_serper_adapter(serper_key))

        # SerpAPI
        serpapi_key = (cfg.get("serpapi") or {}).get("apiKey") or os.environ.get("SERPAPI_API_KEY")
        if serpapi_key:
            self._registry.register("serpapi", create_serpapi_adapter(serpapi_key))

        # Google CSE
        google_key = (cfg.get("google") or {}).get("apiKey") or os.environ.get("GOOGLE_CSE_API_KEY")
        engine_id = (cfg.get("google") or {}).get("engineId") or os.environ.get("GOOGLE_CSE_ENGINE_ID")
        if google_key and engine_id:
            self._registry.register("google", create_google_adapter(google_key, engine_id))

        # Bing
        bing_key = (cfg.get("bing") or {}).get("apiKey") or os.environ.get("BING_API_KEY")
        if bing_key:
            self._registry.register("bing", create_bing_adapter(bing_key))

        # Brave
        brave_key = (cfg.get("brave") or {}).get("apiKey") or os.environ.get("BRAVE_API_KEY")
        if brave_key:
            self._registry.register("brave", create_brave_adapter(brave_key))

        # DataForSEO
        df_login = (cfg.get("dataforseo") or {}).get("login") or os.environ.get("DATAFORSEO_LOGIN")
        df_password = (cfg.get("dataforseo") or {}).get("password") or os.environ.get("DATAFORSEO_PASSWORD")
        if df_login and df_password:
            self._registry.register("dataforseo", create_dataforseo_adapter(df_login, df_password))

        # SearchAPI
        searchapi_key = (cfg.get("searchapi") or {}).get("apiKey") or os.environ.get("SEARCHAPI_API_KEY")
        if searchapi_key:
            self._registry.register("searchapi", create_searchapi_adapter(searchapi_key))

        # ValueSERP
        valueserp_key = (cfg.get("valueserp") or {}).get("apiKey") or os.environ.get("VALUESERP_API_KEY")
        if valueserp_key:
            self._registry.register("valueserp", create_valueserp_adapter(valueserp_key))

        # ScrapingDog
        scrapingdog_key = (cfg.get("scrapingdog") or {}).get("apiKey") or os.environ.get("SCRAPINGDOG_API_KEY")
        if scrapingdog_key:
            self._registry.register("scrapingdog", create_scrapingdog_adapter(scrapingdog_key))

        # Bright Data
        brightdata_key = (cfg.get("brightdata") or {}).get("apiKey") or os.environ.get("BRIGHTDATA_API_KEY")
        if brightdata_key:
            self._registry.register("brightdata", create_brightdata_adapter(brightdata_key))

        # SearchCans
        searchcans_key = (cfg.get("searchcans") or {}).get("apiKey") or os.environ.get("SEARCHCANS_API_KEY")
        if searchcans_key:
            self._registry.register("searchcans", create_searchcans_adapter(searchcans_key))

    async def search(self, request: dict[str, Any] | str) -> dict[str, Any]:
        """Search using a specific provider.

        Provider can be specified as ``"provider/query"`` prefix syntax or uses
        the first available provider that supports the requested type.
        """
        if isinstance(request, str):
            req: dict[str, Any] = {"query": request}
        else:
            req = dict(request)

        # Apply defaults
        defaults = self._config.get("defaults")
        if defaults:
            if req.get("num") is None and defaults.get("num"):
                req["num"] = defaults["num"]
            if req.get("country") is None and defaults.get("country"):
                req["country"] = defaults["country"]
            if req.get("language") is None and defaults.get("language"):
                req["language"] = defaults["language"]
            if req.get("safe") is None and defaults.get("safe") is not None:
                req["safe"] = defaults["safe"]

        # Check for provider prefix in query
        provider_name: str | None = None
        query = req.get("query", "")
        if "/" in query:
            slash_idx = query.index("/")
            maybe_provider = query[:slash_idx]
            if self._registry.get(maybe_provider) or maybe_provider in self._aliases:
                provider_name = self._aliases.get(maybe_provider, maybe_provider)
                req["query"] = query[slash_idx + 1:]

        # Resolve alias
        if provider_name and provider_name in self._aliases:
            provider_name = self._aliases[provider_name]

        if provider_name:
            adapter = self._registry.get(provider_name)
            if not adapter:
                raise AnySerpError(400, f'Provider "{provider_name}" not configured', {"provider_name": provider_name})
            return await adapter.search(req)

        # No provider specified -- use first available that supports the type
        search_type = req.get("type", "web")
        for adapter in self._registry.all():
            if adapter.supports_type(search_type):
                return await adapter.search(req)

        raise AnySerpError(400, "No provider configured. Set an API key for at least one provider.")

    async def search_with_fallback(
        self,
        request: dict[str, Any],
        providers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Search with fallback across multiple providers."""
        provider_list = providers or self._registry.names()
        search_type = request.get("type", "web")

        last_error: Exception | None = None

        for name in provider_list:
            adapter = self._registry.get(name)
            if not adapter or not adapter.supports_type(search_type):
                continue
            try:
                return await adapter.search(request)
            except Exception as err:
                last_error = err

        if last_error:
            raise last_error
        raise AnySerpError(400, "No providers available for fallback")

    async def search_all(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        """Search all configured providers and return combined results."""
        search_type = request.get("type", "web")
        adapters = [a for a in self._registry.all() if a.supports_type(search_type)]

        tasks = [a.search(request) for a in adapters]
        settled = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in settled if isinstance(r, dict)]

    def providers(self) -> list[str]:
        """List configured provider names."""
        return self._registry.names()

    def get_registry(self) -> AnySerpRegistry:
        """Get the registry for direct adapter access."""
        return self._registry
