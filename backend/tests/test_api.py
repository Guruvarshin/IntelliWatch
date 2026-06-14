"""Standalone test: exercise the Phase 7 FastAPI endpoints end-to-end against
the real MongoDB Atlas database and the real Phase 3-6 graph (so /run makes
real OpenAI/Anthropic/MCP calls and takes ~20-30s).

Mints a JWT the same way Auth.js does (HS256, signed with AUTH_SECRET, "sub"
claim as user_id) so app.auth.get_current_user accepts it.

Run with: python -m tests.test_api  (from backend/)
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

load_dotenv()

from app.db import db
from app.main import app

TEST_USER_ID = "test-user-api"


def make_token() -> str:
    payload = {
        "sub": TEST_USER_ID,
        "email": "test-api@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, os.environ["AUTH_SECRET"], algorithm="HS256")


async def main():
    headers = {"Authorization": f"Bearer {make_token()}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create
        resp = await client.post(
            "/competitors",
            json={
                "name": "Vercel",
                "since_days": 7,
                "github_repo": "vercel/next.js",
                "hn_query": "Next.js",
                "youtube_channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                "jobs_board_type": "greenhouse",
                "jobs_board_token": "stripe",
                "pricing_url": "https://www.anthropic.com/pricing",
                "news_query": "Anthropic",
            },
            headers=headers,
        )
        print(f"POST /competitors -> {resp.status_code}")
        assert resp.status_code == 200, resp.text
        competitor = resp.json()
        competitor_id = competitor["_id"]
        print(f"  created competitor {competitor_id}")

        try:
            # List
            resp = await client.get("/competitors", headers=headers)
            print(f"GET /competitors -> {resp.status_code}")
            assert resp.status_code == 200, resp.text
            assert any(c["_id"] == competitor_id for c in resp.json())

            # Get one
            resp = await client.get(f"/competitors/{competitor_id}", headers=headers)
            print(f"GET /competitors/{{id}} -> {resp.status_code}")
            assert resp.status_code == 200, resp.text
            assert resp.json()["name"] == "Vercel"

            # Partial update
            resp = await client.patch(
                f"/competitors/{competitor_id}",
                json={"since_days": 14},
                headers=headers,
            )
            print(f"PATCH /competitors/{{id}} -> {resp.status_code}")
            assert resp.status_code == 200, resp.text
            assert resp.json()["since_days"] == 14
            assert resp.json()["name"] == "Vercel"

            # Run the full graph (real LLM/MCP calls, ~20-30s)
            print("POST /competitors/{id}/run -- running full graph, this may take ~30s...")
            resp = await client.post(
                f"/competitors/{competitor_id}/run", headers=headers, timeout=180
            )
            print(f"POST /competitors/{{id}}/run -> {resp.status_code}")
            assert resp.status_code == 200, resp.text
            run_result = resp.json()
            print(f"  raw_signal_count={run_result['raw_signal_count']} "
                  f"cluster_count={run_result['cluster_count']}")

            # List briefs
            resp = await client.get(f"/competitors/{competitor_id}/briefs", headers=headers)
            print(f"GET /competitors/{{id}}/briefs -> {resp.status_code}")
            assert resp.status_code == 200, resp.text
            briefs = resp.json()
            print(f"  {len(briefs)} brief(s)")
            assert len(briefs) >= 1

            # 404 for nonexistent competitor
            resp = await client.get("/competitors/000000000000000000000000", headers=headers)
            print(f"GET /competitors/<nonexistent> -> {resp.status_code}")
            assert resp.status_code == 404

        finally:
            # Delete
            resp = await client.delete(f"/competitors/{competitor_id}", headers=headers)
            print(f"DELETE /competitors/{{id}} -> {resp.status_code}")
            assert resp.status_code == 200, resp.text

            # Clean up documents written by /run
            for coll_name in ("raw_signals", "extracted_signals", "signal_clusters", "briefs"):
                deleted = await db[coll_name].delete_many({"competitor_id": competitor_id})
                print(f"Cleaned up {deleted.deleted_count} {coll_name} document(s).")


if __name__ == "__main__":
    asyncio.run(main())
