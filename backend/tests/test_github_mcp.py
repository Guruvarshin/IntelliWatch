"""Standalone test: call github-mcp directly against a real repo.

Run with: python -m tests.test_github_mcp  (from backend/)
"""

import asyncio

from dotenv import load_dotenv

from app.mcp.github_mcp import GithubMCPInput, fetch_github_signals

load_dotenv()


async def main():
    result = await fetch_github_signals(
        GithubMCPInput(repo="vercel/next.js", since_days=7)
    )

    print(f"Got {len(result)} signal(s)\n")
    for signal in result:
        print(f"[{signal.signal_type}] {signal.title}")
        print(f"  published_at: {signal.published_at}")
        print(f"  url: {signal.url}")
        print(f"  summary: {signal.summary[:200]}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
