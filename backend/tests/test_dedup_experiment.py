"""Phase 5 experiment: TF-IDF vs embeddings for clustering near-duplicate
signals (the same underlying event reported by different sources, in
different words).

Run with: python -m tests.test_dedup_experiment  (from backend/)
"""

import asyncio

from dotenv import load_dotenv
from openai import AsyncOpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

# Hand-crafted, but realistic: pairs of items describing the *same* event in
# different words (the hard case -- low word overlap, high semantic
# overlap), plus genuinely unrelated items as a negative control.
ITEMS = [
    # Cluster A: same release, two sources, very different wording
    "Next.js 15.1 released with improved caching behavior",
    "Vercel ships a new Next.js version focused on smarter cache handling",
    # Cluster B: same hiring push, two sources, different wording
    "Anthropic careers page lists 20 new machine learning engineer roles",
    "Anthropic is on a hiring spree, opening many new ML positions",
    # Cluster C: same funding news, two sources
    "Anthropic raises new funding round led by major investors",
    "Reports confirm Anthropic closed a large new investment round",
    # Unrelated singletons (negative control)
    "Show HN: I built a tool that visualizes GitHub commit graphs",
    "Acme Corp's pricing page footer text changed slightly",
    "New tutorial video: using the Claude API for tool use",
    "OpenAI community discussion speculates about a future model release",
]


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


def cluster_from_similarity(matrix, threshold: float) -> list[int]:
    n = matrix.shape[0]
    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] >= threshold:
                uf.union(i, j)
    return [uf.find(i) for i in range(n)]


def print_clusters(name: str, labels: list[int]) -> None:
    print(f"\n--- {name} ---")
    groups: dict[int, list[int]] = {}
    for i, label in enumerate(labels):
        groups.setdefault(label, []).append(i)
    for label, members in groups.items():
        tag = "CLUSTER" if len(members) > 1 else "singleton"
        print(f"  [{tag}]")
        for i in members:
            print(f"    {i}: {ITEMS[i]}")


def tfidf_similarity():
    vectors = TfidfVectorizer().fit_transform(ITEMS)
    return cosine_similarity(vectors)


async def embedding_similarity():
    client = AsyncOpenAI()
    response = await client.embeddings.create(
        model="text-embedding-3-small", input=ITEMS
    )
    vectors = [item.embedding for item in response.data]
    return cosine_similarity(vectors)


async def main():
    tfidf_matrix = tfidf_similarity()
    embedding_matrix = await embedding_similarity()

    for threshold in (0.3, 0.5, 0.7):
        print(f"\n========== threshold = {threshold} ==========")
        print_clusters(
            f"TF-IDF (threshold={threshold})",
            cluster_from_similarity(tfidf_matrix, threshold),
        )
        print_clusters(
            f"Embeddings (threshold={threshold})",
            cluster_from_similarity(embedding_matrix, threshold),
        )

    print("\n\nRaw pairwise similarity for the 3 'same event' pairs:")
    for a, b, label in [(0, 1, "Cluster A (Next.js release)"),
                          (2, 3, "Cluster B (Anthropic hiring)"),
                          (4, 5, "Cluster C (Anthropic funding)")]:
        print(f"  {label}: TF-IDF={tfidf_matrix[a][b]:.3f}  Embeddings={embedding_matrix[a][b]:.3f}")


if __name__ == "__main__":
    asyncio.run(main())
