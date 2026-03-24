"""AnySerp -- Unified SERP API router supporting 11 providers."""

from ._client import AnySerp, AnySerpRegistry
from ._errors import AnySerpError
from ._types import (
    AiOverview,
    AiOverviewReference,
    AiOverviewTextBlock,
    AnswerBox,
    AnySerpConfig,
    DataForSeoConfig,
    DateRange,
    DefaultsConfig,
    KnowledgePanel,
    PeopleAlsoAsk,
    ProviderConfig,
    SearchAdapter,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchType,
)
from .providers import (
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

__version__ = "0.1.0"

__all__ = [
    # Client
    "AnySerp",
    "AnySerpRegistry",
    # Errors
    "AnySerpError",
    # Types
    "AiOverview",
    "AiOverviewReference",
    "AiOverviewTextBlock",
    "AnswerBox",
    "AnySerpConfig",
    "DataForSeoConfig",
    "DateRange",
    "DefaultsConfig",
    "KnowledgePanel",
    "PeopleAlsoAsk",
    "ProviderConfig",
    "SearchAdapter",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "SearchType",
    # Provider factories
    "create_bing_adapter",
    "create_brave_adapter",
    "create_brightdata_adapter",
    "create_dataforseo_adapter",
    "create_google_adapter",
    "create_scrapingdog_adapter",
    "create_searchapi_adapter",
    "create_searchcans_adapter",
    "create_serpapi_adapter",
    "create_serper_adapter",
    "create_valueserp_adapter",
]
