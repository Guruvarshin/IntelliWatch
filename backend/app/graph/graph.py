from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    github_agent,
    hn_agent,
    jobs_agent,
    make_brief_writer,
    make_dedup_agent,
    make_extract_agent,
    make_save_to_mongo,
    news_agent,
    scraper_agent,
    supervisor,
    youtube_agent,
)
from app.graph.state import GraphState

SUB_AGENTS = {
    "github_agent": github_agent,
    "hn_agent": hn_agent,
    "jobs_agent": jobs_agent,
    "scraper_agent": scraper_agent,
    "news_agent": news_agent,
    "youtube_agent": youtube_agent,
}


def build_graph(db):
    """Builds and compiles the Phase 4 graph: supervisor fans out to all 6
    sub-agents in parallel, which all fan back in to save_to_mongo."""
    save_to_mongo = make_save_to_mongo(db)
    extract_agent = make_extract_agent(db)
    dedup_agent = make_dedup_agent(db)
    brief_writer = make_brief_writer(db)

    graph = StateGraph(GraphState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("save_to_mongo", save_to_mongo)
    graph.add_node("extract_agent", extract_agent)
    graph.add_node("dedup_agent", dedup_agent)
    graph.add_node("brief_writer", brief_writer)

    for name, fn in SUB_AGENTS.items():
        graph.add_node(name, fn)
        graph.add_edge("supervisor", name)
        graph.add_edge(name, "save_to_mongo")

    graph.add_edge(START, "supervisor")
    graph.add_edge("save_to_mongo", "extract_agent")
    graph.add_edge("extract_agent", "dedup_agent")
    graph.add_edge("dedup_agent", "brief_writer")
    graph.add_edge("brief_writer", END)

    return graph.compile()
