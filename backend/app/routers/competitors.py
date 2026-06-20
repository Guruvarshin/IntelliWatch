from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app.api_keys import get_user_api_keys
from app.auth import get_current_user
from app.db import db
from app.graph.graph import build_graph
from app.graph.state import GraphState
from app.models import CompetitorIn, CompetitorUpdate

router = APIRouter(prefix="/competitors", tags=["competitors"])


def serialize(doc: dict) -> dict:
    return {**doc, "_id": str(doc["_id"])}


async def get_owned_competitor(competitor_id: str, user_id: str) -> dict:
    """Looks up a competitor by id, scoped to the requesting user. Returns
    404 (not 403) for both "doesn't exist" and "belongs to someone else" --
    distinguishing the two would leak which competitor ids exist."""
    try:
        oid = ObjectId(competitor_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Competitor not found")

    competitor = await db.competitors.find_one({"_id": oid, "user_id": user_id})
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return competitor


@router.post("")
async def create_competitor(
    body: CompetitorIn, current_user: dict = Depends(get_current_user)
):
    doc = {
        **body.model_dump(),
        "user_id": current_user["user_id"],
        "pricing_previous_hash": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.competitors.insert_one(doc)
    return serialize({**doc, "_id": result.inserted_id})


@router.get("")
async def list_competitors(current_user: dict = Depends(get_current_user)):
    cursor = db.competitors.find({"user_id": current_user["user_id"]})
    return [serialize(doc) async for doc in cursor]


@router.get("/{competitor_id}")
async def get_competitor(
    competitor_id: str, current_user: dict = Depends(get_current_user)
):
    competitor = await get_owned_competitor(competitor_id, current_user["user_id"])
    return serialize(competitor)


@router.patch("/{competitor_id}")
async def update_competitor(
    competitor_id: str,
    body: CompetitorUpdate,
    current_user: dict = Depends(get_current_user),
):
    competitor = await get_owned_competitor(competitor_id, current_user["user_id"])

    updates = body.model_dump(exclude_unset=True)
    if updates:
        await db.competitors.update_one({"_id": competitor["_id"]}, {"$set": updates})
        competitor = await db.competitors.find_one({"_id": competitor["_id"]})

    return serialize(competitor)


@router.delete("/{competitor_id}")
async def delete_competitor(
    competitor_id: str, current_user: dict = Depends(get_current_user)
):
    competitor = await get_owned_competitor(competitor_id, current_user["user_id"])
    await db.competitors.delete_one({"_id": competitor["_id"]})
    return {"deleted": True}


@router.post("/{competitor_id}/run")
async def run_competitor(
    competitor_id: str, current_user: dict = Depends(get_current_user)
):
    """Runs the full Phase 3-6 graph for this competitor synchronously and
    returns a summary of what was produced. The competitor's per-source
    config fields map directly onto GraphState (decision 20: all optional)."""
    competitor = await get_owned_competitor(competitor_id, current_user["user_id"])
    api_keys = await get_user_api_keys(db, current_user["user_id"])

    graph = build_graph(db)
    initial_state: GraphState = {
        "user_id": current_user["user_id"],
        "competitor_id": str(competitor["_id"]),
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
    result = await graph.ainvoke(initial_state)

    return {
        "raw_signal_count": len(result["raw_signals"]),
        "cluster_count": len(result["signal_clusters"]),
    }


@router.get("/{competitor_id}/briefs")
async def list_briefs(
    competitor_id: str, current_user: dict = Depends(get_current_user)
):
    competitor = await get_owned_competitor(competitor_id, current_user["user_id"])
    cursor = db.briefs.find({"competitor_id": str(competitor["_id"])}).sort(
        "created_at", -1
    )
    return [serialize(doc) async for doc in cursor]
