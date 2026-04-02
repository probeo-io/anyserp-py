"""Runnable demos for anyserp Python SDK.

Usage:
    python examples/basic.py              # Run all examples
    python examples/basic.py search       # Run a specific example
    python examples/basic.py provider
    python examples/basic.py images
    python examples/basic.py news

Requires at least one provider API key:
    export SERPER_API_KEY=...
    export BRAVE_API_KEY=...
"""

from __future__ import annotations

import asyncio
import sys

from anyserp import AnySerp


async def demo_search():
    """Basic web search."""
    print("\n=== Basic Search ===\n")
    client = AnySerp()

    results = await client.search("best python frameworks 2026")

    print(f"Provider: {results.provider}")
    print(f"Results: {len(results.results)}\n")
    for r in results.results[:3]:
        print(f"  {r.title}")
        print(f"  {r.url}\n")


async def demo_provider():
    """Search with a specific provider."""
    print("\n=== Provider-Specific Search ===\n")
    client = AnySerp()

    results = await client.search("python async patterns", provider="serper")

    print(f"Provider: {results.provider}")
    for r in results.results[:3]:
        print(f"  {r.title}")
    print()


async def demo_images():
    """Image search."""
    print("\n=== Image Search ===\n")
    client = AnySerp()

    results = await client.search_images("aurora borealis")

    print(f"Images found: {len(results.results)}")
    for img in results.results[:3]:
        print(f"  {img.title} - {img.url}")
    print()


async def demo_news():
    """News search."""
    print("\n=== News Search ===\n")
    client = AnySerp()

    results = await client.search_news("artificial intelligence")

    for article in results.results[:3]:
        print(f"  {article.title}")
        print(f"  {article.url}\n")


DEMOS = {
    "search": demo_search,
    "provider": demo_provider,
    "images": demo_images,
    "news": demo_news,
}


async def main():
    args = sys.argv[1:]

    if args:
        for name in args:
            if name in DEMOS:
                await DEMOS[name]()
            else:
                print(f"Unknown demo: {name}")
                print(f"Available: {', '.join(DEMOS.keys())}")
                sys.exit(1)
    else:
        for demo_fn in DEMOS.values():
            await demo_fn()


if __name__ == "__main__":
    asyncio.run(main())
