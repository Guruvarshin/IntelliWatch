"""Standalone test: call youtube-mcp directly.
Run with: python -m tests.test_youtube_mcp  (from backend/)"""

import asyncio

from dotenv import load_dotenv  # type: ignore

from app.mcp.youtube_mcp import YouTubeMCPInput, fetch_youtube_signals

load_dotenv()

# "Google for Developers" channel -- posts frequently, good for testing.
GOOGLE_DEVELOPERS_CHANNEL_ID = "UC_x5XG1OV2P6uZZ5FSM9Ttw"


async def main():
    result = await fetch_youtube_signals(
        YouTubeMCPInput(channel_id=GOOGLE_DEVELOPERS_CHANNEL_ID, since_days=14)
    )

    print(f"Got {len(result)} signal(s)\n")
    for signal in result[:5]:
        print(f"[{signal.signal_type}] {signal.title}")
        print(f"  published_at: {signal.published_at}")
        print(f"  url: {signal.url}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
