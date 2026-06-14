from datetime import datetime

from pydantic import BaseModel


class Signal(BaseModel):
    """A single normalized piece of competitive intelligence.

    Every MCP module (github-mcp, hn-mcp, reddit-mcp, ...) returns a list of
    these, regardless of how different their underlying APIs are. This is
    the shape the LangGraph agents and the brief writer will consume.
    """

    source: str
    signal_type: str
    title: str
    summary: str
    url: str
    published_at: datetime
    raw: dict
