"""
Utilities for building lightweight mind map structures from document passages.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List, Mapping, MutableMapping, Sequence

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

from core.models import DocumentPassage


@dataclass(frozen=True)
class MindMapParameters:
    cluster_count: int = 5
    max_neighbors: int = 2
    snippet_length: int = 160


def _clean_snippet(value: str, limit: int) -> str:
    if not value:
        return ""
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit].rstrip()}…"


def _cluster_label(passages: Sequence[DocumentPassage], index: int) -> str:
    for passage in passages:
        heading = (passage.metadata or {}).get("heading")
        if heading:
            return heading

    aggregated = " ".join(p.raw_text for p in passages if p.raw_text)
    if not aggregated:
        return f"Cluster {index + 1}"

    tokens = re.findall(r"[\w\u4e00-\u9fff]+", aggregated)
    counter = Counter(token for token in tokens if len(token) > 1)
    if counter:
        top = " / ".join(word for word, _ in counter.most_common(3))
        return top

    return _clean_snippet(aggregated, 40) or f"Cluster {index + 1}"


def _build_cluster_assignments(embeddings: np.ndarray, desired_clusters: int) -> np.ndarray:
    sample_count = embeddings.shape[0]
    cluster_count = max(1, min(desired_clusters, sample_count))
    if cluster_count == 1 or sample_count == 1:
        return np.zeros(sample_count, dtype=int)

    kmeans = KMeans(
        n_clusters=cluster_count,
        random_state=42,
        n_init=min(10, sample_count),
    )
    return kmeans.fit_predict(embeddings)


def generate_mind_map(
    passages: Sequence[DocumentPassage],
    root_id: str,
    root_label: str,
    *,
    parameters: MindMapParameters | None = None,
) -> Mapping[str, object]:
    params = parameters or MindMapParameters()
    usable_passages: List[DocumentPassage] = [p for p in passages if p.embedding]

    if not usable_passages:
        return {
            "nodes": [
                {
                    "id": root_id,
                    "label": root_label,
                    "type": "root",
                    "meta": {},
                }
            ],
            "edges": [],
            "statistics": {
                "passages": 0,
                "clusters": 0,
                "isolated": 0,
            },
        }

    embeddings = np.vstack([np.array(p.embedding, dtype=np.float32) for p in usable_passages])
    assignments = _build_cluster_assignments(embeddings, params.cluster_count)
    cluster_to_passages: MutableMapping[int, List[int]] = defaultdict(list)
    for idx, cluster_id in enumerate(assignments.tolist()):
        cluster_to_passages[cluster_id].append(idx)

    nodes: List[MutableMapping[str, object]] = [
        {
            "id": root_id,
            "label": root_label,
            "type": "root",
            "meta": {},
        }
    ]
    edges: List[MutableMapping[str, object]] = []

    passage_nodes: List[MutableMapping[str, object]] = []
    passage_index_to_node_id: List[str] = []

    for passage in usable_passages:
        node_id = f"passage-{passage.pk}"
        passage_index_to_node_id.append(node_id)
        passage_nodes.append(
            {
                "id": node_id,
                "type": "passage",
                "label": _clean_snippet(passage.raw_text, params.snippet_length),
                "meta": {
                    "document_id": passage.document_id,
                    "document_name": passage.document.name,
                    "order": passage.order,
                    "part": passage.document_part_id,
                    "metadata": passage.metadata or {},
                },
            }
        )

    nodes.extend(passage_nodes)

    cluster_nodes: List[MutableMapping[str, object]] = []
    for cluster_id, passage_indices in cluster_to_passages.items():
        cluster_node_id = f"cluster-{cluster_id}"
        cluster_passages = [usable_passages[i] for i in passage_indices]
        cluster_nodes.append(
            {
                "id": cluster_node_id,
                "type": "cluster",
                "label": _cluster_label(cluster_passages, cluster_id),
                "meta": {
                    "size": len(passage_indices),
                    "documents": sorted({p.document_id for p in cluster_passages}),
                },
            }
        )
        edges.append(
            {
                "source": root_id,
                "target": cluster_node_id,
                "type": "hierarchy",
            }
        )
        for passage_index in passage_indices:
            edges.append(
                {
                    "source": cluster_node_id,
                    "target": passage_index_to_node_id[passage_index],
                    "type": "membership",
                }
            )

    nodes.extend(cluster_nodes)

    if params.max_neighbors > 0 and len(usable_passages) > 1:
        similarities = cosine_similarity(embeddings)
        seen_edges = set()
        max_neighbors = min(params.max_neighbors, len(usable_passages) - 1)
        for source_index in range(len(usable_passages)):
            ranked = np.argsort(similarities[source_index])[::-1]
            neighbor_count = 0
            for target_index in ranked:
                if source_index == target_index:
                    continue
                key = tuple(sorted((source_index, target_index)))
                if key in seen_edges:
                    continue
                similarity = float(similarities[source_index, target_index])
                if math.isclose(similarity, 1.0):
                    similarity = 1.0
                edges.append(
                    {
                        "source": passage_index_to_node_id[source_index],
                        "target": passage_index_to_node_id[target_index],
                        "type": "similarity",
                        "weight": round(similarity, 4),
                    }
                )
                seen_edges.add(key)
                neighbor_count += 1
                if neighbor_count >= max_neighbors:
                    break

    statistics = {
        "passages": len(usable_passages),
        "clusters": len(cluster_nodes),
        "isolated": 0 if cluster_nodes else len(usable_passages),
    }

    return {
        "nodes": nodes,
        "edges": edges,
        "statistics": statistics,
    }
