"""jobs-mcp: job postings via Greenhouse / Lever public job board APIs.

Optional per competitor (decision 11 in DECISIONS.md) -- not every company
uses one of these two boards. Fail-soft: an unknown/missing board returns
an empty list rather than an error, so one competitor's missing board
doesn't break a multi-competitor run.
"""

from datetime import datetime, timedelta, timezone

import httpx
from pydantic import BaseModel

from app.mcp.schemas import Signal


class JobsMCPInput(BaseModel):
    board_type: str  # "greenhouse" | "lever"
    board_token: str  # company slug on that board, e.g. "stripe"
    since_days: int = 7


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

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if input.board_type == "greenhouse":
                return await _fetch_greenhouse(client, input.board_token, since)
            elif input.board_type == "lever":
                return await _fetch_lever(client, input.board_token, since)
            else:
                return []
    except httpx.HTTPError:
        # Board doesn't exist, wrong token, or API is down -- skip this
        # source for this competitor rather than failing the whole run.
        return []
