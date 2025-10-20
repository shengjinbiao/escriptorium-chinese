"""Utilities for managing semantic embedding generation."""

from __future__ import annotations

import logging
from itertools import islice
from typing import Iterable, List, Optional, Sequence

from django.apps import apps
from django.conf import settings
from django.db import transaction

try:
    from wz_gazetteer.services.embeddings import OpenAIEmbeddingService
except ImportError as exc:  # pragma: no cover - handled at runtime
    OpenAIEmbeddingService = None  # type: ignore[assignment]
    _EMBEDDING_IMPORT_ERROR: Optional[Exception] = exc
else:
    _EMBEDDING_IMPORT_ERROR = None

logger = logging.getLogger(__name__)


DEFAULT_EMBEDDING_BATCH_SIZE = getattr(
    settings, "SEMANTIC_EMBEDDING_BATCH_SIZE", 64
)
DEFAULT_EMBEDDING_MODEL = getattr(
    settings, "SEMANTIC_EMBEDDING_MODEL", None
)
DEFAULT_EMBEDDING_DIM = getattr(
    settings, "SEMANTIC_EMBEDDING_DIM", 1536
)


class EmbeddingServiceNotConfigured(RuntimeError):
    """Raised when the OpenAI embedding client is not yet configured."""


_embedding_service: Optional[OpenAIEmbeddingService] = None


def _passage_model():
    return apps.get_model("core", "DocumentPassage")


def _get_embedding_service() -> OpenAIEmbeddingService:
    if OpenAIEmbeddingService is None:
        raise EmbeddingServiceNotConfigured(
            "wz-gazetteer embedding services are not available. "
            "Install the dependency (e.g. `pip install -e ../yjxz`)."
        ) from _EMBEDDING_IMPORT_ERROR
    global _embedding_service
    if _embedding_service is not None:
        return _embedding_service
    try:
        service = OpenAIEmbeddingService.create()
    except Exception as exc:  # noqa: BLE001
        raise EmbeddingServiceNotConfigured(str(exc)) from exc
    # override model if settings specify
    if DEFAULT_EMBEDDING_MODEL:
        service.client.config.embedding_model = DEFAULT_EMBEDDING_MODEL
    _embedding_service = service
    return service


def pending_passage_ids(limit: Optional[int] = None) -> list:
    """
    Return passage IDs without cached embeddings.
    """

    Passage = _passage_model()
    qs = Passage.objects.filter(embedding__isnull=True).order_by("document", "order")
    if limit:
        qs = qs[:limit]
    return list(qs.values_list("id", flat=True))


def _batched(iterable: Sequence, size: int):
    it = iter(iterable)
    while True:
        batch = list(islice(it, size))
        if not batch:
            break
        yield batch


def generate_embeddings_for_passages(
    passage_ids: Sequence[int], *, force: bool = False
) -> dict:
    """
    Generate embeddings for the provided passages and persist them.
    """

    if not passage_ids:
        return {"processed": 0, "succeeded": 0, "failed": 0}

    Passage = _passage_model()
    passages = list(
        Passage.objects.filter(pk__in=passage_ids).order_by("document", "order")
    )

    if not passages:
        return {"processed": 0, "succeeded": 0, "failed": 0}

    try:
        service = _get_embedding_service()
    except EmbeddingServiceNotConfigured as exc:
        logger.warning("Embedding service not available: %s", exc)
        return {
            "processed": len(passages),
            "succeeded": 0,
            "failed": len(passages),
            "reason": str(exc),
        }

    successes = 0
    failures: List[int] = []

    for batch in _batched(passages, DEFAULT_EMBEDDING_BATCH_SIZE):
        texts = [p.normalized_text or p.raw_text for p in batch]
        try:
            vectors = service.embed_texts(texts)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to generate embeddings: batch starting %s", batch[0].pk)
            failures.extend(p.pk for p in batch)
            continue

        if len(vectors) != len(batch):
            logger.error(
                "Embedding length mismatch: expected %s got %s",
                len(batch),
                len(vectors),
            )
            failures.extend(p.pk for p in batch)
            continue

        with transaction.atomic():
            for passage, vector in zip(batch, vectors):
                if DEFAULT_EMBEDDING_DIM and len(vector) != DEFAULT_EMBEDDING_DIM:
                    logger.warning(
                        "Embedding dimension mismatch for passage %s: expected %s got %s",
                        passage.pk,
                        DEFAULT_EMBEDDING_DIM,
                        len(vector),
                    )
                passage.embedding = vector
                passage.save(update_fields=["embedding", "updated_at"])
                successes += 1

    return {
        "processed": len(passages),
        "succeeded": successes,
        "failed": len(passages) - successes,
        "model": service.client.config.embedding_model,
        "forced": force,
        "failed_ids": failures,
    }


def schedule_document_embedding_refresh(document_ids: Iterable[int]) -> None:
    """
    Hook for queuing embedding regeneration for documents.
    """

    ids = list(document_ids)
    if not ids:
        return
    logger.info(
        "schedule_document_embedding_refresh called for %s document(s).",
        len(ids),
    )


def embed_query_text(text: str) -> List[float]:
    """
    Generate an embedding vector for the provided query string.
    """

    if not text.strip():
        return []

    service = _get_embedding_service()
    try:
        vector = service.embed_query(text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to embed query: %s", exc)
        raise
    return vector or []
