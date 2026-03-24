from __future__ import annotations

from typing import Any, Literal, Protocol, TypedDict


# ── Scalars ───────────────────────────────────────────────────────────────────

SearchType = Literal["web", "images", "news", "videos"]
DateRange = Literal["day", "week", "month", "year"]


# ── Request ───────────────────────────────────────────────────────────────────

class SearchRequest(TypedDict, total=False):
    query: str  # required by convention; total=False for ease of construction
    num: int
    page: int
    country: str
    language: str
    safe: bool
    type: SearchType
    dateRange: DateRange
    includeAiOverview: bool


# ── Response types ────────────────────────────────────────────────────────────

class SearchResult(TypedDict, total=False):
    position: int
    title: str
    url: str
    description: str
    domain: str
    datePublished: str
    thumbnail: str
    imageUrl: str
    imageWidth: int
    imageHeight: int
    source: str
    duration: str
    channel: str


class PeopleAlsoAsk(TypedDict, total=False):
    question: str
    snippet: str
    title: str
    url: str


class KnowledgePanel(TypedDict, total=False):
    title: str
    type: str
    description: str
    source: str
    sourceUrl: str
    attributes: dict[str, str]
    imageUrl: str


class AnswerBox(TypedDict, total=False):
    snippet: str
    title: str
    url: str


class AiOverviewReference(TypedDict, total=False):
    index: int
    title: str
    url: str
    snippet: str
    date: str
    source: str
    thumbnail: str


class AiOverviewTextBlock(TypedDict, total=False):
    type: str  # paragraph | header | ordered_list | unordered_list | table | code_blocks | video
    answer: str
    answerHighlight: str
    items: list[AiOverviewTextBlock]
    table: dict[str, Any]  # {headers: list[str], rows: list[list[str]]}
    language: str
    code: str
    video: dict[str, str | None]
    referenceIndexes: list[int]
    link: str
    relatedSearches: list[dict[str, str]]


class AiOverview(TypedDict, total=False):
    markdown: str
    textBlocks: list[AiOverviewTextBlock]
    references: list[AiOverviewReference]
    pageToken: str


class SearchResponse(TypedDict, total=False):
    provider: str
    query: str
    results: list[SearchResult]
    totalResults: int
    searchTime: float
    relatedSearches: list[str]
    peopleAlsoAsk: list[PeopleAlsoAsk]
    knowledgePanel: KnowledgePanel
    answerBox: AnswerBox
    aiOverview: AiOverview


# ── Config ────────────────────────────────────────────────────────────────────

class ProviderConfig(TypedDict, total=False):
    apiKey: str
    engineId: str


class DataForSeoConfig(TypedDict, total=False):
    login: str
    password: str


class DefaultsConfig(TypedDict, total=False):
    num: int
    country: str
    language: str
    safe: bool


class AnySerpConfig(TypedDict, total=False):
    serper: ProviderConfig
    serpapi: ProviderConfig
    google: ProviderConfig
    bing: ProviderConfig
    brave: ProviderConfig
    dataforseo: DataForSeoConfig
    searchapi: ProviderConfig
    valueserp: ProviderConfig
    scrapingdog: ProviderConfig
    brightdata: ProviderConfig
    searchcans: ProviderConfig
    custom: dict[str, dict[str, str]]
    defaults: DefaultsConfig
    aliases: dict[str, str]


# ── Adapter Protocol ─────────────────────────────────────────────────────────

class SearchAdapter(Protocol):
    @property
    def name(self) -> str: ...

    async def search(self, request: dict[str, Any]) -> dict[str, Any]: ...

    def supports_type(self, search_type: str) -> bool: ...
