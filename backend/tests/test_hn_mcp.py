"""Standalone test: call hn-mcp directly. Run with: python -m tests.test_hn_mcp  (from backend/)"""

import asyncio

from dotenv import load_dotenv # type: ignore

from app.mcp.hn_mcp import HNMCPInput, fetch_hn_signals

load_dotenv()


async def main():
    result = await fetch_hn_signals(HNMCPInput(query="OpenAI", since_days=7))

    print(f"Got {len(result)} signal(s)\n")
    for signal in result[:5]:
        print(f"[{signal.signal_type}] {signal.title}")
        print(f"  published_at: {signal.published_at}")
        print(f"  url: {signal.url}")
        print(f"  summary: {signal.summary[:200]}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
