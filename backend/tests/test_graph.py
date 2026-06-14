"""Standalone test: run the Phase 4 LangGraph fan-out (supervisor -> 6
parallel sub-agents -> save_to_mongo) and confirm all 6 sources populate
raw_signals in MongoDB Atlas in one run.

The config below is a mixed fixture (not one real company) -- it reuses
values already verified individually in Phase 1-2 standalone tests, chosen
to exercise the fan-out mechanism itself (each node independently calling
its MCP tool, results merging via the operator.add reducer).

Run with: python -m tests.test_graph  (from backend/)
"""

import asyncio
import os
from collections import Counter

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from app.graph.graph import build_graph

load_dotenv()


async def main():
    client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    db = client.get_default_database()

    graph = build_graph(db)

    result = await graph.ainvoke(
        {
            "user_id": "test-user",
            "competitor_id": "test-fanout",
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
            "raw_signals": [],
        }
    )

    by_source = Counter(s["source"] for s in result["raw_signals"])
    print(f"\nGraph finished. {len(result['raw_signals'])} signal(s) total in final state:")
    for source, count in by_source.items():
        print(f"  {source}: {count}")

    count = await db.raw_signals.count_documents({"competitor_id": "test-fanout"})
    print(f"\nraw_signals documents in Mongo for test-fanout: {count}")

    sources_in_mongo = await db.raw_signals.distinct("source", {"competitor_id": "test-fanout"})
    print(f"distinct sources in Mongo: {sorted(sources_in_mongo)}")

    extracted_count = await db.extracted_signals.count_documents({"competitor_id": "test-fanout"})
    print(f"\nextracted_signals documents in Mongo for test-fanout: {extracted_count}")

    sample_extracted = await db.extracted_signals.find_one({"competitor_id": "test-fanout"})
    if sample_extracted:
        print(
            f"Sample extraction: [{sample_extracted['source']}/"
            f"{sample_extracted['category']}] "
            f"relevance={sample_extracted['relevance_score']} "
            f"-- {sample_extracted['key_point']}"
        )

    cluster_count = await db.signal_clusters.count_documents({"competitor_id": "test-fanout"})
    print(f"\nsignal_clusters documents in Mongo for test-fanout: {cluster_count}")

    multi_member_clusters = await db.signal_clusters.count_documents(
        {"competitor_id": "test-fanout", "size": {"$gt": 1}}
    )
    print(f"clusters with >1 member: {multi_member_clusters}")

    sample_cluster = await db.signal_clusters.find_one(
        {"competitor_id": "test-fanout", "size": {"$gt": 1}}
    )
    if sample_cluster:
        print(
            f"Sample multi-member cluster ({sample_cluster['size']} members, "
            f"sources={sample_cluster['sources']}): "
            f"{sample_cluster['representative_key_point']}"
        )

    brief = await db.briefs.find_one({"competitor_id": "test-fanout"})
    if brief:
        print(f"\nBrief ({brief['cluster_count']} clusters):\n")
        print(brief["content"])

    deleted = await db.raw_signals.delete_many({"competitor_id": "test-fanout"})
    print(f"\nCleaned up {deleted.deleted_count} raw_signals document(s).")

    deleted_extracted = await db.extracted_signals.delete_many({"competitor_id": "test-fanout"})
    print(f"Cleaned up {deleted_extracted.deleted_count} extracted_signals document(s).")

    deleted_clusters = await db.signal_clusters.delete_many({"competitor_id": "test-fanout"})
    print(f"Cleaned up {deleted_clusters.deleted_count} signal_clusters document(s).")

    deleted_briefs = await db.briefs.delete_many({"competitor_id": "test-fanout"})
    print(f"Cleaned up {deleted_briefs.deleted_count} briefs document(s).")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
