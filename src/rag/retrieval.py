"""Retrieval: dense (vector), sparse (keyword), and hybrid (fused) search.

- dense_search:  pgvector cosine nearest-neighbour (meaning).
- sparse_search: Postgres full-text search (exact words).
- hybrid_search: run both, fuse by rank with Reciprocal Rank Fusion (RRF).

Note on the sparse side: we use Postgres's built-in full-text ranking (`SearchRank`), which
is TF-IDF-family, not literally BM25 (true BM25 needs the pg_search/ParadeDB extension).
Because RRF fuses on *rank position*, not raw scores, the built-in ranker is sufficient:
we only need a sensible keyword ordering, which it provides.
"""

from django.contrib.postgres.search import SearchQuery, SearchRank
from pgvector.django import CosineDistance

from .embeddings import embed_query
from .models import DocumentChunk


DEFAULT_TOP_K = 5
DEFAULT_POOL = 10   # candidates pulled from each method before fusion
DEFAULT_RRF_K = 60  # RRF smoothing constant


def dense_search(question, k=DEFAULT_TOP_K):
    """Nearest chunks by cosine distance (each result carries `.distance`)."""
    query_vector = embed_query(question)
    return list(
        # Compute cosine distance in Postgres for every chunk, then take the k smallest.
        DocumentChunk.objects.annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[:k]  # smaller distance = more similar
    )


def sparse_search(question, k=DEFAULT_TOP_K):
    """Top chunks by Postgres full-text keyword rank (each result carries `.rank`)."""
    # "websearch" parses the query like a search box (quotes, OR, -exclusions) and never errors.
    query = SearchQuery(question, search_type="websearch")
    return list(
        DocumentChunk.objects.annotate(rank=SearchRank("search_vector", query))
        .filter(rank__gt=0)   # drop chunks with no keyword overlap (rank 0)
        .order_by("-rank")[:k]  # higher rank = better keyword match
    )


def _rrf(rank_lists, k=DEFAULT_RRF_K):
    """Reciprocal Rank Fusion.

    Each item scores sum(1 / (k + rank)) across the lists it appears in (rank starts at 1).
    Returns [(item, score)] sorted best-first. Uses rank position only, so lists with
    incompatible score scales (cosine distance vs. keyword rank) can be merged fairly.
    """
    scores = {}
    for ranked in rank_lists:
        for rank, item in enumerate(ranked, start=1):  # position 1, 2, 3, ...
            # Add this list's contribution; an item in several lists accumulates score.
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    # Sort items by total fused score, highest first (kv = (item, score)).
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def hybrid_search(question, k=DEFAULT_TOP_K, pool=DEFAULT_POOL, rrf_k=DEFAULT_RRF_K):
    """Fuse dense + sparse results by RRF (each result carries `.rrf_score`)."""
    dense = dense_search(question, pool)
    sparse = sparse_search(question, pool)

    # Build one list of chunk-ids per method (in rank order) and fuse them, keeping top k.
    # Dry run: dense ranked chunks with ids [7, 3, 9], sparse ranked [3, 7, 5]
    #   -> _rrf([[7, 3, 9], [3, 7, 5]]) scores each id by its position in each list and
    #      returns them best-first, e.g. [(7, .0325), (3, .0325), (5, .016), (9, .016)]:
    #      ids 7 and 3 appear high in BOTH lists so they rank top. [:k] takes the best k.
    fused = _rrf([[c.id for c in dense], [c.id for c in sparse]], k=rrf_k)[:k]

    # id -> chunk lookup across both lists (a chunk in both is stored once).
    by_id = {c.id: c for c in list(dense) + list(sparse)}
    results = []
    for chunk_id, score in fused:
        chunk = by_id[chunk_id]
        chunk.rrf_score = score
        results.append(chunk)
    return results


def search(question, method="hybrid", k=DEFAULT_TOP_K):
    """Dispatch to a retrieval method: 'dense', 'sparse', or 'hybrid'."""
    if method == "dense":
        return dense_search(question, k)
    if method == "sparse":
        return sparse_search(question, k)
    if method == "hybrid":
        return hybrid_search(question, k)
    raise ValueError(f"unknown retrieval method: {method!r}")
