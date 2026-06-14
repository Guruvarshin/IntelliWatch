"""Standalone test: exercise the Phase 8 /internal/run-all endpoint.

Creates a throwaway competitor (real config, same fixture values as
test_api.py), confirms the endpoint rejects requests without/with the wrong
X-Internal-Secret, then confirms a correctly-authenticated call runs the
real graph for that competitor (and any others already in the DB) and
returns a per-competitor summary including it.

Run with: python -m tests.test_internal  (from backend/)
"""

import asyncio
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

load_dotenv()

from app.db import db
from app.main import app

TEST_USER_ID = "test-user-internal"


async def main():
    transport = ASGITransport(app=app)
    secret = os.environ["INTERNAL_SECRET"]

    # Seed a throwaway competitor directly (this endpoint has no per-user auth)
    doc = {
        "name": "Vercel (internal test)",
        "user_id": TEST_USER_ID,
        "since_days": 7,
        "github_repo": "vercel/next.js",
        "hn_query": "Next.js",
        "youtube_channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
        "jobs_board_type": "greenhouse",
        "jobs_board_token": "stripe",
        "pricing_url": "https://www.anthropic.com/pricing",
        "pricing_previous_hash": None,
        "news_query": "Anthropic",
        "blog_rss_url": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.competitors.insert_one(doc)
    competitor_id = str(result.inserted_id)
    print(f"seeded competitor {competitor_id}")

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # No secret
            resp = await client.post("/internal/run-all")
            print(f"POST /internal/run-all (no secret) -> {resp.status_code}")
            assert resp.status_code == 401, resp.text

            # Wrong secret
            resp = await client.post(
                "/internal/run-all", headers={"X-Internal-Secret": "wrong"}
            )
            print(f"POST /internal/run-all (wrong secret) -> {resp.status_code}")
            assert resp.status_code == 401, resp.text

            # Correct secret -- runs the real graph for every competitor in the DB
            print("POST /internal/run-all (correct secret) -- running, this may take a while...")
            resp = await client.post(
                "/internal/run-all",
                headers={"X-Internal-Secret": secret},
                timeout=600,
            )
            print(f"POST /internal/run-all (correct secret) -> {resp.status_code}")
            assert resp.status_code == 200, resp.text

            body = resp.json()
            print(f"  ran {body['ran']} competitor(s)")
            for r in body["results"]:
                print(f"  - {r['name']} ({r['competitor_id']}): {r['status']}")

            ours = next(r for r in body["results"] if r["competitor_id"] == competitor_id)
            assert ours["status"] == "ok", ours
            print(f"  our competitor: raw_signal_count={ours['raw_signal_count']} "
                  f"cluster_count={ours['cluster_count']}")

    finally:
        await db.competitors.delete_one({"_id": result.inserted_id})
        for coll_name in ("raw_signals", "extracted_signals", "signal_clusters", "briefs"):
            deleted = await db[coll_name].delete_many({"competitor_id": competitor_id})
            print(f"Cleaned up {deleted.deleted_count} {coll_name} document(s).")


if __name__ == "__main__":
    asyncio.run(main())
