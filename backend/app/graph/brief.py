"""Phase 6: brief synthesis via Claude Sonnet.

Turns this run's signal_clusters into a short weekly digest, optionally
diffing against the previous brief for "what's new/changed since last week."
"""

from anthropic import AsyncAnthropic

MODEL = "claude-sonnet-4-6"


def _format_clusters(clusters: list[dict]) -> str:
    parts = []
    for cluster in clusters:
        header = (
            f"- {cluster['size']} signal(s) "
            f"[sources: {', '.join(cluster['sources'])}; "
            f"categories: {', '.join(cluster['categories'])}]"
        )
        points = "\n".join(f"    - {kp}" for kp in cluster["key_points"])
        parts.append(f"{header}\n{points}")
    return "\n".join(parts)


async def write_brief(
    clusters: list[dict],
    previous_brief: str | None,
    competitor_id: str,
    api_key: str | None = None,
) -> str:
    """api_key: per-user BYOK Anthropic key (decision 2/Phase 9b). If None,
    AsyncAnthropic() falls back to the ANTHROPIC_API_KEY env var."""
    client = AsyncAnthropic(api_key=api_key)

    prompt = (
        f"You are writing a weekly competitive intelligence digest about "
        f"the competitor '{competitor_id}'.\n\n"
        f"Here are this week's signal clusters (each cluster is one story, "
        f"possibly seen across multiple sources -- 'size' is how many raw "
        f"signals support it):\n\n{_format_clusters(clusters)}\n\n"
    )

    if previous_brief:
        prompt += (
            f"Here is last week's brief for context. Call out what's new "
            f"or changed since then where relevant:\n\n{previous_brief}\n\n"
        )
    else:
        prompt += "This is the first brief for this competitor -- there is no prior week to compare against.\n\n"

    prompt += (
        "Write a concise weekly digest in plain markdown. Group items into "
        "sections (e.g. Product & Engineering, Hiring, Funding & Pricing, "
        "Community). Skip sections with nothing notable. Prioritize "
        "clusters with more sources/signals and higher apparent relevance. "
        "Keep it tight -- a few bullets per section."
    )

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
