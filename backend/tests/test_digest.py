"""Standalone test: exercise the Phase 8.5 /internal/send-digest endpoint.

Looks up the real user account (by email, must already exist via signup),
seeds a throwaway competitor + brief for that user, confirms the endpoint
rejects requests without/with the wrong X-Internal-Secret, then confirms a
correctly-authenticated call sends a real digest email via Resend.

Run with: python -m tests.test_digest  (from backend/)
"""

import asyncio
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

load_dotenv()

from app.db import db
from app.main import app

TEST_USER_EMAIL = "guruprinting2003@gmail.com"


async def main():
    transport = ASGITransport(app=app)
    secret = os.environ["INTERNAL_SECRET"]

    # Resend's sandbox sender (onboarding@resend.dev) can only deliver to the
    # Resend account owner's own email. Borrow an existing test user's
    # account and temporarily point its email there for this run, then
    # restore it -- avoids needing a real signup with that address.
    user = await db.users.find_one({})
    assert user, "No users in db.users -- sign up at least one user via the frontend first"
    user_id = str(user["_id"])
    original_email = user["email"]
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"email": TEST_USER_EMAIL}})
    print(f"using user {user_id} (temporarily {TEST_USER_EMAIL}, was {original_email})")

    # Seed a throwaway competitor + brief for this user
    competitor_doc = {
        "name": "Vercel (digest test)",
        "user_id": user_id,
        "since_days": 7,
        "created_at": datetime.now(timezone.utc),
    }
    competitor_result = await db.competitors.insert_one(competitor_doc)
    competitor_id = str(competitor_result.inserted_id)
    print(f"seeded competitor {competitor_id}")

    brief_doc = {
        "user_id": user_id,
        "competitor_id": competitor_id,
        "content": "## Product & Engineering\n- Shipped a new feature.\n\n## Hiring\n- Opened 3 new roles.",
        "cluster_count": 2,
        "created_at": datetime.now(timezone.utc),
    }
    await db.briefs.insert_one(brief_doc)
    print("seeded brief")

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # No secret
            resp = await client.post("/internal/send-digest")
            print(f"POST /internal/send-digest (no secret) -> {resp.status_code}")
            assert resp.status_code == 401, resp.text

            # Wrong secret
            resp = await client.post(
                "/internal/send-digest", headers={"X-Internal-Secret": "wrong"}
            )
            print(f"POST /internal/send-digest (wrong secret) -> {resp.status_code}")
            assert resp.status_code == 401, resp.text

            # Correct secret -- sends real email(s) via Resend
            resp = await client.post(
                "/internal/send-digest",
                headers={"X-Internal-Secret": secret},
                timeout=60,
            )
            print(f"POST /internal/send-digest (correct secret) -> {resp.status_code}")
            assert resp.status_code == 200, resp.text

            body = resp.json()
            print(f"  sent {body['sent']} digest(s)")
            for r in body["results"]:
                print(f"  - {r['user_id']}: {r['status']}" + (f" ({r.get('reason')})" if r.get("reason") else ""))

            ours = next(r for r in body["results"] if r["user_id"] == user_id)
            assert ours["status"] == "sent", ours
            print(f"  our user: competitor_count={ours['competitor_count']}")
            print(f"  check {TEST_USER_EMAIL} for the digest email")

    finally:
        await db.competitors.delete_one({"_id": competitor_result.inserted_id})
        await db.briefs.delete_many({"competitor_id": competitor_id})
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"email": original_email}})
        print("Cleaned up seeded competitor, brief, and restored user email.")


if __name__ == "__main__":
    asyncio.run(main())
