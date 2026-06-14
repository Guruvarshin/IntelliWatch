"""Standalone test: call jobs-mcp directly against real Greenhouse + Lever
boards. Run with: python -m tests.test_jobs_mcp  (from backend/)"""

import asyncio

from dotenv import load_dotenv

from app.mcp.jobs_mcp import JobsMCPInput, fetch_jobs_signals

load_dotenv()


async def main():
    for board_type, token in [("greenhouse", "stripe"), ("lever", "netflix")]:
        result = await fetch_jobs_signals(
            JobsMCPInput(board_type=board_type, board_token=token, since_days=7)
        )
        print(f"{board_type}/{token}: {len(result)} signal(s)")
        for signal in result[:3]:
            print(f"  [{signal.signal_type}] {signal.title}")
            print(f"    published_at: {signal.published_at}")
            print(f"    url: {signal.url}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
