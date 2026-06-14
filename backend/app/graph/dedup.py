"""Phase 5: deduplication via embedding similarity + union-find clustering.

Chosen over TF-IDF after a side-by-side experiment (test_dedup_experiment.py):
TF-IDF cosine similarity for genuinely duplicate events (same release/funding
news, reported in different words by different sources) scored 0.09-0.21 --
indistinguishable from unrelated items. Embeddings scored 0.66-0.82 for the
same pairs, with a clean gap below unrelated items at threshold 0.5.
"""

from collections import defaultdict

from openai import AsyncOpenAI
from sklearn.metrics.pairwise import cosine_similarity

SIMILARITY_THRESHOLD = 0.5


class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


async def embed_texts(texts: list[str], api_key: str | None = None) -> list[list[float]]:
    """api_key: per-user BYOK OpenAI key (decision 2/Phase 9b). If None,
    AsyncOpenAI() falls back to the OPENAI_API_KEY env var."""
    if not texts:
        return []

    client = AsyncOpenAI(api_key=api_key)
    response = await client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [item.embedding for item in response.data]


def cluster_by_similarity(matrix, threshold: float = SIMILARITY_THRESHOLD) -> list[list[int]]:
    """Groups indices into clusters via union-find: any pair with
    similarity >= threshold ends up in the same cluster (clusters can grow
    transitively, e.g. A~B and B~C merges A, B, C even if A~C alone is below
    threshold)."""
    n = len(matrix)
    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] >= threshold:
                uf.union(i, j)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[uf.find(i)].append(i)
    return list(groups.values())
