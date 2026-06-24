"""github-mcp: repo activity (releases + commits) via the GitHub REST API.

This module follows the MCP "tool" pattern: a typed input schema, a typed
output (list[Signal]), and a single async function that does the work. It
has no dependency on FastAPI, LangGraph, or Mongo -- it can be called and
tested in isolation.
"""

import os
from datetime import datetime, timedelta, timezone

import httpx
from pydantic import BaseModel

from app.mcp.schemas import Signal

GITHUB_API_BASE = "https://api.github.com"


class GithubMCPInput(BaseModel):
    repo: str  # "owner/name", e.g. "vercel/next.js"
    since_days: int = 7


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def _fetch_releases(
    client: httpx.AsyncClient, repo: str, since: datetime
) -> list[Signal]:
    resp = await client.get(f"{GITHUB_API_BASE}/repos/{repo}/releases")
    resp.raise_for_status()

    signals = []
    for release in resp.json():
        published_at = datetime.fromisoformat(
            release["published_at"].replace("Z", "+00:00")
        )
        if published_at < since:
            continue

        signals.append(
            Signal(
                source="github",
                signal_type="release",
                title=f"{repo}: {release['name'] or release['tag_name']}",
                summary=(release["body"] or "")[:1000],
                url=release["html_url"],
                published_at=published_at,
                raw=release,
            )
        )

    return signals


async def _fetch_commits(
    client: httpx.AsyncClient, repo: str, since: datetime
) -> list[Signal]:
    resp = await client.get(
        f"{GITHUB_API_BASE}/repos/{repo}/commits",
        params={"since": since.isoformat(), "per_page": 100},
    )
    resp.raise_for_status()

    commits = resp.json()
    if not commits:
        return []

    messages = [c["commit"]["message"].splitlines()[0] for c in commits[:10]]
    latest = commits[0]
    published_at = datetime.fromisoformat(
        latest["commit"]["author"]["date"].replace("Z", "+00:00")
    )

    summary = f"{len(commits)} commit(s) in the last {(_now() - since).days} day(s):\n" + "\n".join(
        f"- {m}" for m in messages
    )

    return [
        Signal(
            source="github",
            signal_type="commit_activity",
            title=f"{repo}: {len(commits)} commits this week",
            summary=summary,
            url=f"https://github.com/{repo}/commits",
            published_at=published_at,
            raw={"count": len(commits), "messages": messages},
        )
    ]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def fetch_github_signals(input: GithubMCPInput) -> list[Signal]:
    since = _now() - timedelta(days=input.since_days)

    async with httpx.AsyncClient(headers=_headers(), timeout=10.0, follow_redirects=True) as client:
        releases = await _fetch_releases(client, input.repo, since)
        commits = await _fetch_commits(client, input.repo, since)

    return releases + commits
