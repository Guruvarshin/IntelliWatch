"""hn-mcp: Hacker News mentions via the Algolia HN Search API.

No API key required. Algolia indexes all HN stories/comments and exposes a
free search endpoint, including a date-range filter, which is exactly what
a weekly digest needs.
"""

from datetime import datetime, timedelta, timezone

import httpx
from pydantic import BaseModel

from app.mcp.schemas import Signal

HN_API_BASE = "https://hn.algolia.com/api/v1"


class HNMCPInput(BaseModel):
    query: str  # e.g. company name
    since_days: int = 7


async def fetch_hn_signals(input: HNMCPInput) -> list[Signal]:
    since = datetime.now(timezone.utc) - timedelta(days=input.since_days)
    since_ts = int(since.timestamp())

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{HN_API_BASE}/search_by_date",
            params={
                "query": input.query,
                "tags": "story",
                "numericFilters": f"created_at_i>{since_ts}",
            },
        )
        resp.raise_for_status()

    query_lower = input.query.lower()

    signals = []
    for hit in resp.json().get("hits", []):
        title = hit.get("title") or ""
        story_text = hit.get("story_text") or ""
        if query_lower not in title.lower() and query_lower not in story_text.lower():
            # Algolia's search is relevance/typo-tolerant, not strict
            # substring matching -- this drops hits that don't actually
            # contain the query at all (e.g. "OpenAI" matching "Open").
            continue

        published_at = datetime.fromtimestamp(hit["created_at_i"], tz=timezone.utc)
        discussion_url = f"https://news.ycombinator.com/item?id={hit['objectID']}"

        summary_parts = [
            f"{hit.get('points', 0)} points, {hit.get('num_comments', 0)} comments."
        ]
        if story_text:
            summary_parts.append(story_text[:500])

        signals.append(
            Signal(
                source="hn",
                signal_type="story",
                title=hit.get("title") or "(untitled)",
                summary=" ".join(summary_parts),
                url=discussion_url,
                published_at=published_at,
                raw=hit,
            )
        )

    return signals
