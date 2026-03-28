# anyserp

Unified SERP API router for Python. Route search requests across Google, Bing, Brave, and more with a single API. Self-hosted, zero fees.

## Install

```bash
pip install anyserp
```

## Quick Start

Set your API keys as environment variables:

```bash
export SERPER_API_KEY=...
export BRAVE_API_KEY=...
```

```python
import asyncio
from anyserp import AnySerp

async def main():
    client = AnySerp()

    # Search with the first available provider
    results = await client.search("best python frameworks")
    print(results["results"][0]["title"], results["results"][0]["url"])

asyncio.run(main())
```

## Supported Providers

| Provider | Env Var | Web | Images | News | Videos |
|----------|---------|-----|--------|------|--------|
| Serper | `SERPER_API_KEY` | Yes | Yes | Yes | Yes |
| SerpAPI | `SERPAPI_API_KEY` | Yes | Yes | Yes | Yes |
| Google CSE | `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ENGINE_ID` | Yes | Yes | No | No |
| Bing | `BING_API_KEY` | Yes | Yes | Yes | Yes |
| Brave | `BRAVE_API_KEY` | Yes | Yes | Yes | Yes |
| DataForSEO | `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` | Yes | No | Yes | No |
| SearchAPI | `SEARCHAPI_API_KEY` | Yes | Yes | Yes | Yes |
| ValueSERP | `VALUESERP_API_KEY` | Yes | Yes | Yes | Yes |
| ScrapingDog | `SCRAPINGDOG_API_KEY` | Yes | Yes | Yes | No |
| Bright Data | `BRIGHTDATA_API_KEY` | Yes | Yes | Yes | Yes |
| SearchCans | `SEARCHCANS_API_KEY` | Yes | No | Yes | No |

## Provider Routing

Specify a provider with `provider/query` format:

```python
# Use a specific provider
results = await client.search("serper/python frameworks")

# Or just search with the first available
results = await client.search("python frameworks")
```

## Search Options

```python
results = await client.search({
    "query": "python frameworks",
    "num": 20,             # number of results
    "page": 2,             # page number
    "country": "us",       # country code
    "language": "en",      # language code
    "safe": True,          # safe search
    "type": "web",         # web, images, news, videos
    "dateRange": "month",  # day, week, month, year
})
```

## Fallback Routing

Try multiple providers in order. If one fails, the next is attempted:

```python
results = await client.search_with_fallback(
    {"query": "python frameworks"},
    ["serper", "brave", "bing"],
)
```

## Search All Providers

Search all configured providers and get combined results:

```python
all_results = await client.search_all({"query": "python frameworks"})

for result in all_results:
    print(f"{result['provider']}: {len(result['results'])} results")
```

## Unified Response Format

All providers return the same response shape:

```python
{
    "provider": "serper",
    "query": "python frameworks",
    "results": [
        {
            "position": 1,
            "title": "...",
            "url": "...",
            "description": "...",
            "domain": "...",
            "datePublished": "...",
            # Image fields
            "imageUrl": "...",
            "imageWidth": 800,
            "imageHeight": 600,
            # News fields
            "source": "...",
            # Video fields
            "duration": "...",
            "channel": "...",
        }
    ],
    "totalResults": 1000000,
    "searchTime": 250,
    "relatedSearches": ["..."],
    "peopleAlsoAsk": [{"question": "...", "snippet": "...", "title": "...", "url": "..."}],
    "knowledgePanel": {"title": "...", "type": "...", "description": "..."},
    "answerBox": {"snippet": "...", "title": "...", "url": "..."},
    "aiOverview": {"markdown": "...", "textBlocks": [...], "references": [...]},
}
```

## Configuration

### Programmatic

```python
client = AnySerp({
    "serper": {"api_key": "..."},
    "brave": {"api_key": "..."},
    "google": {"api_key": "...", "engine_id": "..."},
    "dataforseo": {"login": "...", "password": "..."},
    "searchapi": {"api_key": "..."},
    "valueserp": {"api_key": "..."},
    "scrapingdog": {"api_key": "..."},
    "brightdata": {"api_key": "..."},
    "searchcans": {"api_key": "..."},
    "defaults": {
        "num": 10,
        "country": "us",
        "language": "en",
        "safe": True,
    },
    "aliases": {
        "fast": "serper",
        "default": "brave",
    },
})
```

### Environment Variables

```bash
export SERPER_API_KEY=...
export SERPAPI_API_KEY=...
export GOOGLE_CSE_API_KEY=...
export GOOGLE_CSE_ENGINE_ID=...
export BING_API_KEY=...
export BRAVE_API_KEY=...
export DATAFORSEO_LOGIN=...
export DATAFORSEO_PASSWORD=...
export SEARCHAPI_API_KEY=...
export VALUESERP_API_KEY=...
export SCRAPINGDOG_API_KEY=...
export BRIGHTDATA_API_KEY=...
export SEARCHCANS_API_KEY=...
```

## People Also Ask

Available from 8 providers (Serper, SerpAPI, SearchAPI, ValueSERP, DataForSEO, ScrapingDog, Bright Data, SearchCans):

```python
results = await client.search("how to start an LLC")
for paa in results.get("peopleAlsoAsk", []):
    print(paa["question"], paa.get("snippet", ""))
```

## AI Overview

Fetch Google's AI-generated overview content (requires SearchAPI):

```python
results = await client.search({
    "query": "how to start an LLC",
    "includeAiOverview": True,
})

if results.get("aiOverview"):
    print(results["aiOverview"]["markdown"])
    for ref in results["aiOverview"]["references"]:
        print(f"  [{ref['index']}] {ref['title']} - {ref['url']}")
```

## See Also

| Package | Description |
|---|---|
| [@probeo/anyserp](https://github.com/probeo-io/anyserp) | TypeScript version of this package |
| [anyserp-go](https://github.com/probeo-io/anyserp-go) | Go version of this package |
| [anymodel-py](https://github.com/probeo-io/anymodel-py) | Unified LLM router for Python |
| [workflow-py](https://github.com/probeo-io/workflow-py) | Stage-based pipeline engine for Python |

## License

MIT
