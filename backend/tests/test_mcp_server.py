"""Standalone test: connect to the IntelliWatch MCP server in-process
(no separate process/transport -- FastMCP's in-memory Client connects
directly to the `mcp` object) and call each tool.

Run with: python -m tests.test_mcp_server  (from backend/)
"""

import asyncio

from dotenv import load_dotenv
from fastmcp import Client

from app.mcp.server import mcp

load_dotenv()


async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("Registered tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        print()

        result = await client.call_tool(
            "github_signals", {"repo": "vercel/next.js", "since_days": 7}
        )
        signals = result.structured_content["result"]
        print(f"github_signals -> {len(signals)} signal(s)")
        if signals:
            print(f"  e.g. [{signals[0]['signal_type']}] {signals[0]['title']}")

        result = await client.call_tool(
            "youtube_signals",
            {"channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw", "since_days": 14},
        )
        signals = result.structured_content["result"]
        print(f"\nyoutube_signals -> {len(signals)} signal(s)")
        if signals:
            print(f"  e.g. [{signals[0]['signal_type']}] {signals[0]['title']}")


if __name__ == "__main__":
    asyncio.run(main())
