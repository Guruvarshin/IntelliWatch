"""youtube-mcp: company YouTube channel activity via channel RSS feed.

No API key required. Surfaces marketing/product communication signals --
new videos (demos, launches, tutorials, announcements) a competitor
publishes publicly.
"""

import calendar
from datetime import datetime, timedelta, timezone

import feedparser
import httpx
from pydantic import BaseModel

from app.mcp.schemas import Signal

YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml"


class YouTubeMCPInput(BaseModel):
    channel_id: str  # YouTube channel ID, starts with "UC..."
    since_days: int = 7


async def fetch_youtube_signals(input: YouTubeMCPInput) -> list[Signal]:
    since = datetime.now(timezone.utc) - timedelta(days=input.since_days)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                YOUTUBE_RSS_URL, params={"channel_id": input.channel_id}
            )
            resp.raise_for_status()
    except httpx.HTTPError:
        return []

    feed = feedparser.parse(resp.text)

    signals = []
    for entry in feed.entries:
        if not entry.get("published_parsed"):
            continue

        published_at = datetime.fromtimestamp(
            calendar.timegm(entry.published_parsed), tz=timezone.utc
        )
        if published_at < since:
            continue

        signals.append(
            Signal(
                source="youtube",
                signal_type="video",
                title=entry.title,
                summary=entry.get("summary", ""),
                url=entry.link,
                published_at=published_at,
                raw={
                    "title": entry.title,
                    "summary": entry.get("summary", ""),
                    "link": entry.link,
                    "published": entry.get("published", ""),
                    "author": entry.get("author", ""),
                },
            )
        )

    return signals
