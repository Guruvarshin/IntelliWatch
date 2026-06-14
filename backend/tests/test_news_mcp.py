"""Standalone test: call news-mcp directly. Run with: python -m tests.test_news_mcp  (from backend/)"""

import asyncio

from dotenv import load_dotenv

from app.mcp.news_mcp import NewsMCPInput, fetch_news_signals

load_dotenv()


async def main():
    result = await fetch_news_signals(
        NewsMCPInput(
            query="Anthropic",
            since_days=7,
            blog_rss_url="https://www.anthropic.com/rss.xml",
        )
    )

    print(f"Got {len(result)} signal(s)\n")
    for signal in result[:5]:
        print(f"[{signal.signal_type}] {signal.title}")
        print(f"  published_at: {signal.published_at}")
        print(f"  url: {signal.url}")
        print(f"  summary: {signal.summary[:200]}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
