import os
import traceback

from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException

from app.api_keys import get_user_api_keys
from app.db import db
from app.digest import format_digest_email, send_email
from app.graph.graph import build_graph

router = APIRouter(prefix="/internal", tags=["internal"])


def verify_internal_secret(x_internal_secret: str | None = Header(default=None)) -> None:
    """Auth for machine-to-machine calls (the weekly cron), separate from the
    user-facing JWT auth in app.auth. The cron has no user session -- it
    proves itself via a shared secret instead."""
    expected = os.environ["INTERNAL_SECRET"]
    if not x_internal_secret or x_internal_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid internal secret")


@router.post("/run-all", dependencies=[Depends(verify_internal_secret)])
async def run_all():
    """Runs the Phase 3-6 graph for every competitor across every user.
    Called weekly by GitHub Actions. Each competitor is run independently --
    one failing run is recorded and skipped rather than aborting the batch."""
    graph = build_graph(db)

    results = []
    async for competitor in db.competitors.find({}):
        competitor_id = str(competitor["_id"])
        try:
            api_keys = await get_user_api_keys(db, competitor["user_id"])
            result = await graph.ainvoke(
                {
                    "user_id": competitor["user_id"],
                    "competitor_id": competitor_id,
                    "competitor_name": competitor.get("name", ""),
                    "since_days": competitor.get("since_days", 7),
                    "github_repo": competitor.get("github_repo"),
                    "hn_query": competitor.get("hn_query"),
                    "youtube_channel_id": competitor.get("youtube_channel_id"),
                    "jobs_board_type": competitor.get("jobs_board_type"),
                    "jobs_board_token": competitor.get("jobs_board_token"),
                    "pricing_url": competitor.get("pricing_url"),
                    "pricing_previous_hash": competitor.get("pricing_previous_hash"),
                    "news_query": competitor.get("news_query"),
                    "blog_rss_url": competitor.get("blog_rss_url"),
                    "openai_api_key": api_keys["openai_api_key"],
                    "anthropic_api_key": api_keys["anthropic_api_key"],
                    "raw_signals": [],
                }
            )
            results.append(
                {
                    "competitor_id": competitor_id,
                    "name": competitor.get("name"),
                    "status": "ok",
                    "raw_signal_count": len(result["raw_signals"]),
                    "cluster_count": len(result["signal_clusters"]),
                }
            )
        except Exception:
            print(f"[run_all] competitor {competitor_id} failed:\n{traceback.format_exc()}")
            results.append(
                {
                    "competitor_id": competitor_id,
                    "name": competitor.get("name"),
                    "status": "error",
                }
            )

    print(f"[run_all] ran {len(results)} competitor(s)")
    return {"ran": len(results), "results": results}


@router.post("/send-digest", dependencies=[Depends(verify_internal_secret)])
async def send_digest():
    """Sends each user one email containing their most recent brief for
    every competitor they track. Users with zero briefs, or whose user
    document has no email, are skipped (not errors)."""
    results = []

    for user_id in await db.competitors.distinct("user_id"):
        briefs = []
        async for competitor in db.competitors.find({"user_id": user_id}):
            brief = await db.briefs.find_one(
                {"competitor_id": str(competitor["_id"])},
                sort=[("created_at", -1)],
            )
            if brief:
                briefs.append({"name": competitor.get("name", "Unknown"), "content": brief["content"]})

        if not briefs:
            results.append({"user_id": user_id, "status": "skipped", "reason": "no briefs"})
            continue

        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("email"):
            results.append({"user_id": user_id, "status": "skipped", "reason": "no email"})
            continue

        subject, html_body, text_body = format_digest_email(briefs)
        try:
            await send_email(user["email"], subject, html_body, text_body)
            results.append(
                {"user_id": user_id, "status": "sent", "competitor_count": len(briefs)}
            )
        except Exception:
            print(f"[send_digest] user {user_id} failed:\n{traceback.format_exc()}")
            results.append({"user_id": user_id, "status": "error"})

    sent = sum(1 for r in results if r["status"] == "sent")
    print(f"[send_digest] sent {sent} digest(s)")
    return {"sent": sent, "results": results}
