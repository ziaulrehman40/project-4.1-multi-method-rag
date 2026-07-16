"""Graph retrieval: seed by edge-embedding similarity, then expand by traversal.

A lightweight "local search": find the edges most semantically related to the question
(the seeds), collect their entities, then walk `hops` steps outward to gather the connected
subgraph — the evidence the answer is built from.
"""

from django.db.models import Q
from pgvector.django import CosineDistance

from rag.embeddings import embed_query  # reuse Stage 1 embeddings

from .models import Relationship


DEFAULT_SEEDS = 5
DEFAULT_HOPS = 1
DEFAULT_MAX_EDGES = 20


def graph_search(question, seeds=DEFAULT_SEEDS, hops=DEFAULT_HOPS, max_edges=DEFAULT_MAX_EDGES):
    """Return a subgraph (list of edges, seeds first) relevant to the question."""
    query_vector = embed_query(question)

    # Seed: the edges whose sentence-embedding is closest to the question.
    seed_edges = list(
        Relationship.objects.exclude(embedding=None)
        .annotate(distance=CosineDistance("embedding", query_vector))
        .select_related("subject", "object")
        .order_by("distance")[:seeds]
    )

    # Breadth-first expansion outward from the seed nodes, one "hop" (layer) per iteration.
    collected = {edge.id: edge for edge in seed_edges}          # edges gathered so far (by id)
    frontier = {e.subject_id for e in seed_edges} | {e.object_id for e in seed_edges}  # nodes to expand this round
    seen_nodes = set(frontier)                                  # nodes already expanded (avoid revisiting)

    for _ in range(hops):
        if len(collected) >= max_edges:
            break
        # All edges touching any node in the current frontier.
        neighbours = (
            Relationship.objects.filter(Q(subject_id__in=frontier) | Q(object_id__in=frontier))
            .select_related("subject", "object")
        )
        next_frontier = set()
        for edge in neighbours:
            collected.setdefault(edge.id, edge)
            # Any endpoint we haven't expanded yet becomes the next layer to explore.
            for node_id in (edge.subject_id, edge.object_id):
                if node_id not in seen_nodes:
                    next_frontier.add(node_id)
        seen_nodes |= next_frontier
        frontier = next_frontier

    # Seeds first (most relevant), then the expanded edges; capped at max_edges.
    expanded = [e for e in collected.values() if e not in seed_edges]
    return (seed_edges + expanded)[:max_edges]
