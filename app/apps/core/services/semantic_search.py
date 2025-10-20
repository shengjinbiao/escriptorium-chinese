"""Semantic search helpers combining OpenAI embeddings and Elasticsearch kNN."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional

from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch import exceptions as es_exceptions

from core.services.embedding import (
    EmbeddingServiceNotConfigured,
    embed_query_text,
)

logger = logging.getLogger(__name__)


def _build_filter_query(
    documents: Optional[Iterable[int]] = None,
    document_parts: Optional[Iterable[int]] = None,
) -> Optional[dict]:
    filters: List[dict] = []
    if documents:
        filters.append({"terms": {"document_id": list(set(documents))}})
    if document_parts:
        filters.append({"terms": {"document_part_id": list(set(document_parts))}})
    if not filters:
        return None
    return {"bool": {"filter": filters}}


def semantic_search(
    query: str,
    *,
    limit: int = 5,
    documents: Optional[Iterable[int]] = None,
    document_parts: Optional[Iterable[int]] = None,
    num_candidates: Optional[int] = None,
) -> Dict[str, object]:
    """
    Run a semantic search on the passage index using the OpenAI embedding service.
    """

    limit = max(1, min(limit, 50))
    candidates = num_candidates or max(limit * 4, 100)

    try:
        query_vector = embed_query_text(query)
    except EmbeddingServiceNotConfigured as exc:
        logger.warning("Semantic search unavailable: %s", exc)
        return {
            "hits": [],
            "error": str(exc),
        }

    if not query_vector:
        return {"hits": []}

    es_client = Elasticsearch(settings.ELASTICSEARCH_URL)
    try:
        if not es_client.ping():
            raise RuntimeError("Elasticsearch is not reachable.")
    except es_exceptions.ElasticsearchException as exc:
        logger.exception("Unable to reach Elasticsearch: %s", exc)
        return {"hits": [], "error": "elasticsearch_unreachable"}

    filter_query = _build_filter_query(documents, document_parts)

    try:
        response = es_client.search(
            index=settings.ELASTICSEARCH_SEMANTIC_INDEX,
            knn={
                "field": "embedding",
                "query_vector": query_vector,
                "k": limit,
                "num_candidates": candidates,
            },
            query=filter_query,
            _source=["document_id", "document_part_id", "passage_order", "raw_text", "metadata"],
        )
    except es_exceptions.NotFoundError:
        return {"hits": [], "error": "index_missing"}
    except es_exceptions.ElasticsearchException as exc:
        logger.exception("Semantic search failure: %s", exc)
        return {"hits": [], "error": "elasticsearch_error"}

    hits = []
    for hit in response.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        hits.append(
            {
                "id": hit.get("_id"),
                "score": hit.get("_score"),
                "document_id": source.get("document_id"),
                "document_part_id": source.get("document_part_id"),
                "order": source.get("passage_order"),
                "text": source.get("raw_text"),
                "metadata": source.get("metadata") or {},
            }
        )

    return {"hits": hits}
