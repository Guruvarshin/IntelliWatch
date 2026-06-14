"""Phase 4b: GPT-4o-mini extraction.

Turns raw signals (one shape per source -- a GitHub release, an HN story, a
job posting, ...) into a small, uniform structured summary that Phase 5
(dedup) and Phase 6 (brief writer) can consume without caring which of the
6 sources a signal came from.
"""

from collections import defaultdict
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel

# Per-source cap before sending to the LLM. Some sources (e.g. jobs-mcp,
# which has no "since X days" filter and returns every open role) can return
# far more items than others -- capping per source keeps the prompt bounded
# and roughly balances coverage across sources rather than letting one
# source crowd out the rest.
PER_SOURCE_CAP = 15

CATEGORIES = ["product", "hiring", "pricing", "funding", "community", "other"]


class ExtractedSignal(BaseModel):
    index: int  # position in the input list this extraction refers to
    category: Literal["product", "hiring", "pricing", "funding", "community", "other"]
    relevance_score: float  # 0.0-1.0, how noteworthy this is for a competitor digest
    key_point: str  # one-sentence takeaway


class ExtractionResult(BaseModel):
    signals: list[ExtractedSignal]


def cap_signals(raw_signals: list[dict], raw_signal_ids: list[str]) -> list[tuple[dict, str]]:
    """Groups signals by source, sorts each group by published_at (newest
    first), and keeps at most PER_SOURCE_CAP per source."""
    by_source: dict[str, list[tuple[dict, str]]] = defaultdict(list)
    for signal, signal_id in zip(raw_signals, raw_signal_ids):
        by_source[signal["source"]].append((signal, signal_id))

    capped = []
    for pairs in by_source.values():
        pairs.sort(key=lambda pair: pair[0]["published_at"], reverse=True)
        capped.extend(pairs[:PER_SOURCE_CAP])

    return capped


async def extract_signals(signals: list[dict], api_key: str | None = None) -> list[ExtractedSignal]:
    """Sends a batch of signals to GPT-4o-mini and gets back structured
    category/relevance/key_point extractions, one per input signal.

    api_key: per-user BYOK OpenAI key (decision 2/Phase 9b). If None,
    AsyncOpenAI() falls back to the OPENAI_API_KEY env var."""
    if not signals:
        return []

    client = AsyncOpenAI(api_key=api_key)

    items = "\n".join(
        f"{i}. [{s['source']}/{s['signal_type']}] {s['title']} -- {s['summary'][:300]}"
        for i, s in enumerate(signals)
    )

    response = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You analyze competitive intelligence signals about a "
                    "company. For each numbered item, classify it into one "
                    f"of these categories: {', '.join(CATEGORIES)}. Score "
                    "relevance 0.0-1.0 for how noteworthy it is in a weekly "
                    "competitor digest (routine/low-signal items score low). "
                    "Write a one-sentence key_point summarizing it. Return "
                    "one extraction per input item, using its index."
                ),
            },
            {"role": "user", "content": items},
        ],
        response_format=ExtractionResult,
    )

    return response.choices[0].message.parsed.signals
