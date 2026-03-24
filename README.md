# anyserp

Unified SERP API router for Python. 11 providers — one interface. Self-hosted, zero fees.

## Install

```bash
pip install anyserp
```

## Quick Start

```bash
export SERPER_API_KEY=...
```

```python
import asyncio
from anyserp import AnySerp

async def main():
    client = AnySerp()
    results = await client.search("best python frameworks")
    for r in results["results"]:
        print(r["title"], r["url"])

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

```python
# Use a specific provider
results = await client.search("serper/python frameworks")

# Or search with the first available
results = await client.search("python frameworks")
```

## Search Options

```python
results = await client.search({
    "query": "python frameworks",
    "num": 20,
    "page": 2,
    "country": "us",
    "language": "en",
    "safe": True,
    "type": "web",
    "dateRange": "month",
})
```

## Fallback Routing

```python
results = await client.search_with_fallback(
    {"query": "python frameworks"},
    ["serper", "brave", "bing"],
)
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

## Configuration

```python
client = AnySerp({
    "serper": {"api_key": "..."},
    "brave": {"api_key": "..."},
    "defaults": {"num": 10, "country": "us"},
    "aliases": {"fast": "serper"},
})
```

## Also Available

- **Node.js**: [`@probeo/anyserp`](https://github.com/probeo-io/anyserp) on npm
- **Go**: [`anyserp-go`](https://github.com/probeo-io/anyserp-go)

## License

MIT
