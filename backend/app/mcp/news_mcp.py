"""news-mcp: general press via Google News RSS + optional company blog RSS.

Both are plain RSS/Atom feeds -- no API key needed. Google News RSS search
covers "general press mentions"; an optional per-competitor blog RSS feed
covers official announcements straight from the source.
"""

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.mcp.schemas import Signal

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


class NewsMCPInput(BaseModel):
    query: str  # e.g. company name
    since_days: int = 7
    blog_rss_url: str | None = None


async def _fetch_feed(client: httpx.AsyncClient, url: str, params: dict | None = None):
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    return feedparser.parse(resp.text).entries


def _entry_to_signal(entry, signal_type: str, since: datetime) -> Signal | None:
    published = entry.get("published") or entry.get("updated")
    try:
        published_at = parsedate_to_datetime(published)
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        published_at = datetime.now(timezone.utc)

    if published_at < since:
        return None

    raw_summary = entry.get("summary", "")
    summary = BeautifulSoup(raw_summary, "html.parser").get_text(separator=" ").strip()

    return Signal(
        source="news",
        signal_type=signal_type,
        title=entry.get("title", "(untitled)"),
        summary=summary[:1000],
        url=entry.get("link", ""),
        published_at=published_at,
        raw={"title": entry.get("title"), "summary": raw_summary},
    )


async def fetch_news_signals(input: NewsMCPInput) -> list[Signal]:
    since = datetime.now(timezone.utc) - timedelta(days=input.since_days)
    signals = []

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        entries = await _fetch_feed(
            client,
            GOOGLE_NEWS_RSS,
            params={"q": input.query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
        )
        for entry in entries:
            signal = _entry_to_signal(entry, "press", since)
            if signal:
                signals.append(signal)

        if input.blog_rss_url:
            try:
                blog_entries = await _fetch_feed(client, input.blog_rss_url)
                for entry in blog_entries:
                    signal = _entry_to_signal(entry, "blog_post", since)
                    if signal:
                        signals.append(signal)
            except httpx.HTTPError:
                pass  # blog feed down/missing -- fail soft, press results still returned

    return signals
