"""jobs-mcp: job postings via SerpApi (Google Jobs) as primary source,
with Greenhouse / Lever as optional additional sources if board credentials
are provided on the competitor.

SerpApi runs automatically for every competitor using the company name --
no per-competitor config needed beyond SERPAPI_KEY in the environment.
Greenhouse/Lever still work as an extra signal layer if jobs_board_type and
jobs_board_token are set. Results are deduplicated by URL before returning.
"""

import os
from datetime import datetime, timedelta, timezone

import httpx
from pydantic import BaseModel

from app.mcp.schemas import Signal


class JobsMCPInput(BaseModel):
    company_name: str
    since_days: int = 7
    board_type: str | None = None   # "greenhouse" | "lever" -- optional extra source
    board_token: str | None = None  # company slug on that board


def _parse_relative_date(posted_at: str) -> datetime:
    """Convert SerpApi relative date strings ('3 days ago') to UTC datetime."""
    now = datetime.now(timezone.utc)
    try:
        n = int(posted_at.split()[0])
        if "hour" in posted_at:
            return now - timedelta(hours=n)
        if "day" in posted_at:
            return now - timedelta(days=n)
        if "week" in posted_at:
            return now - timedelta(weeks=n)
        if "month" in posted_at:
            return now - timedelta(days=30 * n)
    except (ValueError, IndexError):
        pass
    return now


async def _fetch_serpapi(company_name: str, since_days: int) -> list[Signal]:
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return []

    try:
        from serpapi import GoogleSearch  # type: ignore
    except ImportError:
        return []

    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    date_chip = "date_posted:week" if since_days <= 7 else "date_posted:month"

    try:
        search = GoogleSearch({
            "engine": "google_jobs",
            "q": company_name,
            "chips": date_chip,
            "api_key": api_key,
        })
        results = search.get_dict()
    except Exception:
        return []

    signals = []
    for job in results.get("jobs_results", []):
        posted_at_str = job.get("detected_extensions", {}).get("posted_at", "")
        published_at = _parse_relative_date(posted_at_str) if posted_at_str else datetime.now(timezone.utc)

        if published_at < since:
            continue

        related = job.get("related_links") or []
        url = (
            related[0]["link"]
            if related
            else job.get("share_link", f"https://www.google.com/search?q={company_name}+jobs&htidocid={job.get('job_id','')}")
        )

        location = job.get("location", "")
        title = f"{job['title']} ({location})" if location else job["title"]

        signals.append(
            Signal(
                source="jobs",
                signal_type="job_posting",
                title=title,
                summary=f"{company_name} is hiring: {job['title']} via {job.get('via', 'Google Jobs')}. Location: {location or 'unspecified'}.",
                url=url,
                published_at=published_at,
                raw=job,
            )
        )

    return signals


async def _fetch_greenhouse(
    client: httpx.AsyncClient, token: str, since: datetime
) -> list[Signal]:
    resp = await client.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs")
    resp.raise_for_status()

    signals = []
    for job in resp.json().get("jobs", []):
        updated_at = datetime.fromisoformat(job["updated_at"].replace("Z", "+00:00"))
        if updated_at < since:
            continue

        location = (job.get("location") or {}).get("name", "")
        title = f"{job['title']} ({location})" if location else job["title"]

        signals.append(
            Signal(
                source="jobs",
                signal_type="job_posting",
                title=title,
                summary=f"Open role on {token}'s Greenhouse board, last updated {updated_at.date()}.",
                url=job["absolute_url"],
                published_at=updated_at,
                raw=job,
            )
        )

    return signals


async def _fetch_lever(
    client: httpx.AsyncClient, token: str, since: datetime
) -> list[Signal]:
    resp = await client.get(
        f"https://api.lever.co/v0/postings/{token}", params={"mode": "json"}
    )
    resp.raise_for_status()

    signals = []
    for job in resp.json():
        created_at = datetime.fromtimestamp(job["createdAt"] / 1000, tz=timezone.utc)
        if created_at < since:
            continue

        location = (job.get("categories") or {}).get("location", "")
        title = f"{job['text']} ({location})" if location else job["text"]

        signals.append(
            Signal(
                source="jobs",
                signal_type="job_posting",
                title=title,
                summary=f"New role posted on {token}'s Lever board.",
                url=job["hostedUrl"],
                published_at=created_at,
                raw=job,
            )
        )

    return signals


async def fetch_jobs_signals(input: JobsMCPInput) -> list[Signal]:
    since = datetime.now(timezone.utc) - timedelta(days=input.since_days)
    signals: list[Signal] = []

    # Primary: SerpApi Google Jobs (runs for every competitor when SERPAPI_KEY is set)
    signals.extend(await _fetch_serpapi(input.company_name, input.since_days))

    # Additional: Greenhouse / Lever if credentials are provided
    if input.board_type and input.board_token:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if input.board_type == "greenhouse":
                    signals.extend(await _fetch_greenhouse(client, input.board_token, since))
                elif input.board_type == "lever":
                    signals.extend(await _fetch_lever(client, input.board_token, since))
        except httpx.HTTPError:
            pass

    # Deduplicate by URL
    seen: set[str] = set()
    deduped: list[Signal] = []
    for s in signals:
        if s.url not in seen:
            seen.add(s.url)
            deduped.append(s)

    return deduped
