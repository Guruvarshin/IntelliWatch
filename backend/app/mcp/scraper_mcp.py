"""scraper-mcp: pricing page change detection via BeautifulSoup.

Fail-soft by design (decision 12): any network/parsing error returns an
empty list, never an exception -- a single competitor's broken pricing
page must not take down a multi-competitor run.

The "diff" is content-hash based: the caller (Phase 3+, once raw_signals
exists in Mongo) passes in the previous run's hash. If the hash is
unchanged, nothing happened -> no signal. If it changed, emit a
"pricing_change" signal. On the very first run (no previous hash), emit a
baseline "pricing_snapshot" signal so future runs have something to diff
against.
"""

import hashlib
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.mcp.schemas import Signal


class ScraperMCPInput(BaseModel):
    url: str
    previous_hash: str | None = None


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())


async def fetch_pricing_signal(input: ScraperMCPInput) -> list[Signal]:
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                input.url, headers={"User-Agent": "Mozilla/5.0 (IntelliWatch bot)"}
            )
            resp.raise_for_status()
    except httpx.HTTPError:
        return []

    text = _extract_text(resp.text)
    content_hash = hashlib.sha256(text.encode()).hexdigest()

    if input.previous_hash == content_hash:
        return []  # no change since last run

    is_first_run = input.previous_hash is None
    signal_type = "pricing_snapshot" if is_first_run else "pricing_change"
    title = (
        f"Pricing page baseline captured: {input.url}"
        if is_first_run
        else f"Pricing page changed: {input.url}"
    )

    return [
        Signal(
            source="scraper",
            signal_type=signal_type,
            title=title,
            summary=text[:1000],
            url=input.url,
            published_at=datetime.now(timezone.utc),
            raw={"hash": content_hash, "previous_hash": input.previous_hash},
        )
    ]
