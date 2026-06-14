import operator
from typing import Annotated, TypedDict


class GraphState(TypedDict):
    """State threaded through the graph for one competitor's weekly run.

    Each sub-agent node calls its MCP tool and returns its own signals
    (just a list[dict], not the accumulated total) -- the
    Annotated[list[dict], operator.add] reducer tells LangGraph to
    concatenate every parallel node's contribution into raw_signals,
    rather than the default "last write wins" behavior.

    Per-source config fields are optional (str | None): a competitor may
    not have every source configured (decision 11 -- jobs boards are
    optional, and the same applies to youtube/blog/etc).
    """

    user_id: str
    competitor_id: str
    since_days: int

    github_repo: str | None
    hn_query: str | None
    youtube_channel_id: str | None
    jobs_board_type: str | None
    jobs_board_token: str | None
    pricing_url: str | None
    pricing_previous_hash: str | None
    news_query: str | None
    blog_rss_url: str | None

    # Per-user BYOK keys (Phase 9b, decision 2). None means "use the env
    # var fallback" -- see app.api_keys.get_user_api_keys.
    openai_api_key: str | None
    anthropic_api_key: str | None

    raw_signals: Annotated[list[dict], operator.add]

    # Written once by save_to_mongo, after insert_many populates each doc's
    # _id -- no reducer needed, single writer.
    raw_signal_ids: list[str]

    # Written once by extract_agent: the extracted_signals docs it inserted
    # (with _id as str), for dedup_agent to cluster.
    extracted_signals: list[dict]

    # Written once by dedup_agent: the signal_clusters docs it inserted
    # (with _id as str), for brief_writer to synthesize.
    signal_clusters: list[dict]
