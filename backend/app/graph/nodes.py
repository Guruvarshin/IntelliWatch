from datetime import datetime, timezone

from fastmcp import Client
from sklearn.metrics.pairwise import cosine_similarity

from app.graph.brief import write_brief
from app.graph.dedup import cluster_by_similarity, embed_texts
from app.graph.extraction import cap_signals, extract_signals
from app.graph.state import GraphState
from app.mcp.server import mcp


async def supervisor(state: GraphState) -> dict:
    """Deterministic routing node.

    All 6 sub-agents fan out from here in parallel (per decision 6:
    routing is deterministic, not LLM-chosen). Each sub-agent checks its
    own config field and returns [] if that source isn't configured for
    this competitor -- so "fan out to everything" and "skip unconfigured
    sources" are the same thing from the supervisor's point of view.
    """
    print(f"[supervisor] routing competitor {state['competitor_id']}")
    return {}


async def github_agent(state: GraphState) -> dict:
    if not state.get("github_repo"):
        return {"raw_signals": []}

    async with Client(mcp) as client:
        result = await client.call_tool(
            "github_signals",
            {"repo": state["github_repo"], "since_days": state["since_days"]},
        )

    signals = result.structured_content["result"]
    print(f"[github_agent] {len(signals)} signal(s)")
    return {"raw_signals": signals}


async def hn_agent(state: GraphState) -> dict:
    if not state.get("hn_query"):
        return {"raw_signals": []}

    async with Client(mcp) as client:
        result = await client.call_tool(
            "hn_signals",
            {"query": state["hn_query"], "since_days": state["since_days"]},
        )

    signals = result.structured_content["result"]
    print(f"[hn_agent] {len(signals)} signal(s)")
    return {"raw_signals": signals}


async def jobs_agent(state: GraphState) -> dict:
    if not state.get("jobs_board_type") or not state.get("jobs_board_token"):
        return {"raw_signals": []}

    async with Client(mcp) as client:
        result = await client.call_tool(
            "jobs_signals",
            {
                "board_type": state["jobs_board_type"],
                "board_token": state["jobs_board_token"],
                "since_days": state["since_days"],
            },
        )

    signals = result.structured_content["result"]
    print(f"[jobs_agent] {len(signals)} signal(s)")
    return {"raw_signals": signals}


async def scraper_agent(state: GraphState) -> dict:
    if not state.get("pricing_url"):
        return {"raw_signals": []}

    async with Client(mcp) as client:
        result = await client.call_tool(
            "scraper_signal",
            {
                "url": state["pricing_url"],
                "previous_hash": state.get("pricing_previous_hash"),
            },
        )

    signals = result.structured_content["result"]
    print(f"[scraper_agent] {len(signals)} signal(s)")
    return {"raw_signals": signals}


async def news_agent(state: GraphState) -> dict:
    if not state.get("news_query"):
        return {"raw_signals": []}

    async with Client(mcp) as client:
        result = await client.call_tool(
            "news_signals",
            {
                "query": state["news_query"],
                "since_days": state["since_days"],
                "blog_rss_url": state.get("blog_rss_url"),
            },
        )

    signals = result.structured_content["result"]
    print(f"[news_agent] {len(signals)} signal(s)")
    return {"raw_signals": signals}


async def youtube_agent(state: GraphState) -> dict:
    if not state.get("youtube_channel_id"):
        return {"raw_signals": []}

    async with Client(mcp) as client:
        result = await client.call_tool(
            "youtube_signals",
            {
                "channel_id": state["youtube_channel_id"],
                "since_days": state["since_days"],
            },
        )

    signals = result.structured_content["result"]
    print(f"[youtube_agent] {len(signals)} signal(s)")
    return {"raw_signals": signals}


def make_save_to_mongo(db):
    """Returns a node that persists state['raw_signals'] to the
    raw_signals collection, tagged with user_id/competitor_id/fetched_at."""

    async def save_to_mongo(state: GraphState) -> dict:
        docs = [
            {
                **signal,
                "user_id": state["user_id"],
                "competitor_id": state["competitor_id"],
                "fetched_at": datetime.now(timezone.utc),
            }
            for signal in state["raw_signals"]
        ]

        if docs:
            await db.raw_signals.insert_many(docs)

        print(f"[save_to_mongo] inserted {len(docs)} signal(s)")
        return {"raw_signal_ids": [str(doc["_id"]) for doc in docs]}

    return save_to_mongo


def make_extract_agent(db):
    """Returns a node that caps raw_signals per source, sends the capped
    batch to GPT-4o-mini for structured extraction, and persists the
    results to the extracted_signals collection, linked back to their
    raw_signals document via raw_signal_id."""

    async def extract_agent(state: GraphState) -> dict:
        capped = cap_signals(state["raw_signals"], state["raw_signal_ids"])
        extracted = await extract_signals(
            [signal for signal, _ in capped], api_key=state.get("openai_api_key")
        )

        docs = []
        for item in extracted:
            signal, signal_id = capped[item.index]
            docs.append(
                {
                    "raw_signal_id": signal_id,
                    "user_id": state["user_id"],
                    "competitor_id": state["competitor_id"],
                    "source": signal["source"],
                    "category": item.category,
                    "relevance_score": item.relevance_score,
                    "key_point": item.key_point,
                    "fetched_at": datetime.now(timezone.utc),
                }
            )

        if docs:
            await db.extracted_signals.insert_many(docs)

        print(
            f"[extract_agent] extracted {len(docs)} signal(s) "
            f"from {len(capped)} capped (of {len(state['raw_signals'])} total)"
        )
        return {"extracted_signals": [{**doc, "_id": str(doc["_id"])} for doc in docs]}

    return extract_agent


def make_dedup_agent(db):
    """Returns a node that clusters extracted_signals by embedding
    similarity (per decision 22: text-embedding-3-small, threshold 0.5,
    union-find) and persists the clusters to signal_clusters."""

    async def dedup_agent(state: GraphState) -> dict:
        extracted = state["extracted_signals"]

        if not extracted:
            print("[dedup_agent] no extracted signals, skipping")
            return {"signal_clusters": []}

        embeddings = await embed_texts(
            [item["key_point"] for item in extracted], api_key=state.get("openai_api_key")
        )
        matrix = cosine_similarity(embeddings)
        groups = cluster_by_similarity(matrix)

        docs = []
        for group in groups:
            members = [extracted[i] for i in group]
            docs.append(
                {
                    "user_id": state["user_id"],
                    "competitor_id": state["competitor_id"],
                    "extracted_signal_ids": [m["_id"] for m in members],
                    "raw_signal_ids": [m["raw_signal_id"] for m in members],
                    "sources": sorted({m["source"] for m in members}),
                    "categories": sorted({m["category"] for m in members}),
                    "representative_key_point": members[0]["key_point"],
                    "key_points": [m["key_point"] for m in members],
                    "size": len(members),
                    "fetched_at": datetime.now(timezone.utc),
                }
            )

        if docs:
            await db.signal_clusters.insert_many(docs)

        print(f"[dedup_agent] {len(docs)} cluster(s) from {len(extracted)} extracted signal(s)")
        return {"signal_clusters": [{**doc, "_id": str(doc["_id"])} for doc in docs]}

    return dedup_agent


def make_brief_writer(db):
    """Returns a node that synthesizes state['signal_clusters'] into a
    weekly digest via Claude Sonnet, diffing against the previous brief for
    this competitor if one exists, and persists the result to briefs."""

    async def brief_writer(state: GraphState) -> dict:
        clusters = state["signal_clusters"]

        if not clusters:
            print("[brief_writer] no clusters, skipping")
            return {}

        previous = await db.briefs.find_one(
            {"competitor_id": state["competitor_id"]},
            sort=[("created_at", -1)],
        )
        previous_content = previous["content"] if previous else None

        content = await write_brief(
            clusters,
            previous_content,
            state["competitor_id"],
            api_key=state.get("anthropic_api_key"),
        )

        await db.briefs.insert_one(
            {
                "user_id": state["user_id"],
                "competitor_id": state["competitor_id"],
                "content": content,
                "cluster_count": len(clusters),
                "created_at": datetime.now(timezone.utc),
            }
        )

        print(f"[brief_writer] wrote brief ({len(content)} chars) from {len(clusters)} cluster(s)")
        return {}

    return brief_writer
