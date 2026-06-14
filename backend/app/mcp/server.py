"""IntelliWatch MCP server -- wraps all 6 data-source modules as MCP tools
on a single FastMCP server.

Each tool here is a thin wrapper: it builds the module's typed input,
calls its `fetch_*_signals` function (the logic already built and tested
standalone in Phases 1-2), and returns the resulting signals as plain
dicts (FastMCP serializes tool outputs to JSON, so plain dicts/lists are
the right return type, not Pydantic models).

This single `mcp` object is what gets connected to in-process (decision:
"MCP-in-process") -- LangGraph's MCP client (Phase 3) talks to this same
object via FastMCP's in-memory transport, no separate server/process.
"""

from fastmcp import FastMCP

from app.mcp.github_mcp import GithubMCPInput, fetch_github_signals
from app.mcp.hn_mcp import HNMCPInput, fetch_hn_signals
from app.mcp.jobs_mcp import JobsMCPInput, fetch_jobs_signals
from app.mcp.news_mcp import NewsMCPInput, fetch_news_signals
from app.mcp.scraper_mcp import ScraperMCPInput, fetch_pricing_signal
from app.mcp.youtube_mcp import YouTubeMCPInput, fetch_youtube_signals

mcp = FastMCP("intelliwatch")


@mcp.tool()
async def github_signals(repo: str, since_days: int = 7) -> list[dict]:
    """Get recent GitHub release and commit activity for a repo (owner/name)."""
    signals = await fetch_github_signals(GithubMCPInput(repo=repo, since_days=since_days))
    return [s.model_dump(mode="json") for s in signals]


@mcp.tool()
async def hn_signals(query: str, since_days: int = 7) -> list[dict]:
    """Search Hacker News stories mentioning a query (e.g. company name)."""
    signals = await fetch_hn_signals(HNMCPInput(query=query, since_days=since_days))
    return [s.model_dump(mode="json") for s in signals]


@mcp.tool()
async def jobs_signals(board_type: str, board_token: str, since_days: int = 7) -> list[dict]:
    """Get recent job postings from a Greenhouse or Lever board.

    board_type must be "greenhouse" or "lever". Returns [] if the board
    doesn't exist (optional per competitor).
    """
    signals = await fetch_jobs_signals(
        JobsMCPInput(board_type=board_type, board_token=board_token, since_days=since_days)
    )
    return [s.model_dump(mode="json") for s in signals]


@mcp.tool()
async def scraper_signal(url: str, previous_hash: str | None = None) -> list[dict]:
    """Check a pricing page for changes since the last known content hash.

    Returns [] on fetch failure, [] if unchanged, or one signal
    (pricing_snapshot on first run, pricing_change if the hash differs).
    """
    signals = await fetch_pricing_signal(ScraperMCPInput(url=url, previous_hash=previous_hash))
    return [s.model_dump(mode="json") for s in signals]


@mcp.tool()
async def news_signals(
    query: str, since_days: int = 7, blog_rss_url: str | None = None
) -> list[dict]:
    """Search Google News for a query, optionally also pulling a company blog RSS feed."""
    signals = await fetch_news_signals(
        NewsMCPInput(query=query, since_days=since_days, blog_rss_url=blog_rss_url)
    )
    return [s.model_dump(mode="json") for s in signals]


@mcp.tool()
async def youtube_signals(channel_id: str, since_days: int = 7) -> list[dict]:
    """Get recent video uploads from a company's YouTube channel (channel ID, starts with "UC")."""
    signals = await fetch_youtube_signals(
        YouTubeMCPInput(channel_id=channel_id, since_days=since_days)
    )
    return [s.model_dump(mode="json") for s in signals]


if __name__ == "__main__":
    mcp.run()
