"""Standalone test: call scraper-mcp directly. Run with: python -m tests.test_scraper_mcp  (from backend/)

Demonstrates both the first-run (no previous_hash -> snapshot) and the
second-run (same hash -> no signal) cases.
"""

import asyncio

from dotenv import load_dotenv

from app.mcp.scraper_mcp import ScraperMCPInput, fetch_pricing_signal

load_dotenv()


async def main():
    # Demonstrates fail-soft: bot-blocked sites return [] instead of raising.
    blocked = await fetch_pricing_signal(ScraperMCPInput(url="https://openai.com/pricing"))
    print(f"Bot-blocked page: {len(blocked)} signal(s) (expect 0, fail-soft)\n")

    url = "https://www.anthropic.com/pricing"

    first = await fetch_pricing_signal(ScraperMCPInput(url=url))
    print(f"First run: {len(first)} signal(s)")
    for signal in first:
        print(f"  [{signal.signal_type}] {signal.title}")
        print(f"    hash: {signal.raw['hash'][:12]}...")

    if not first:
        print("  (fetch failed -- fail-soft returned empty list)")
        return

    previous_hash = first[0].raw["hash"]

    second = await fetch_pricing_signal(
        ScraperMCPInput(url=url, previous_hash=previous_hash)
    )
    print(f"\nSecond run (same hash): {len(second)} signal(s) (expect 0)")

    third = await fetch_pricing_signal(
        ScraperMCPInput(url=url, previous_hash="deliberately-wrong-hash")
    )
    print(f"Third run (different hash): {len(third)} signal(s) (expect 1)")
    for signal in third:
        print(f"  [{signal.signal_type}] {signal.title}")


if __name__ == "__main__":
    asyncio.run(main())
