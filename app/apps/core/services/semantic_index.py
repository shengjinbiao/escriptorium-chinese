"""
Helpers for building semantic passage indexes for documents and projects.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Sequence

from django.apps import apps
from django.core.management import call_command

from core.services.embedding import (
    EmbeddingServiceNotConfigured,
    generate_embeddings_for_passages,
)

logger = logging.getLogger(__name__)


class SemanticIndexingError(RuntimeError):
    """Raised when semantic indexing fails due to an unexpected error."""


def _unique_document_ids(document_ids: Iterable[int]) -> List[int]:
    return sorted({int(pk) for pk in document_ids if pk is not None})


def build_semantic_index(
    document_ids: Sequence[int],
    *,
    reset_passages: bool = True,
    force_embeddings: bool = False,
    drop_index: bool = False,
) -> dict:
    """
    Generate passages, embeddings and index entries for the provided documents.
    """

    doc_ids = _unique_document_ids(document_ids)
    if not doc_ids:
        return {
            "documents": 0,
            "passages": 0,
            "embedding": {"processed": 0, "succeeded": 0, "failed": 0},
        }

    try:
        _run_generate_passages(doc_ids, reset_passages=reset_passages)
        passage_ids = list(
            _passage_model()
            .objects.filter(document_id__in=doc_ids)
            .values_list("pk", flat=True)
        )
        embedding_result = generate_embeddings_for_passages(
            passage_ids, force=force_embeddings
        )
        if embedding_result.get("reason") and embedding_result.get("succeeded", 0) == 0:
            raise EmbeddingServiceNotConfigured(embedding_result["reason"])
        _run_index_semantic(doc_ids, drop_index=drop_index)
    except (EmbeddingServiceNotConfigured, SemanticIndexingError):
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unexpected error while building semantic index for %s", doc_ids
        )
        raise SemanticIndexingError(str(exc)) from exc

    return {
        "documents": len(doc_ids),
        "passages": len(passage_ids),
        "embedding": embedding_result,
    }


def _run_generate_passages(
    document_ids: Sequence[int], *, reset_passages: bool = True
) -> None:
    args: List[str] = ["--documents", *map(str, document_ids)]
    if reset_passages:
        args.append("--reset")
    logger.info("Generating passages for documents %s", document_ids)
    call_command("generate_passages", *args)


def _run_index_semantic(
    document_ids: Sequence[int], *, drop_index: bool = False
) -> None:
    args: List[str] = []
    if drop_index:
        args.append("--drop")
    args.extend(["--documents", *map(str, document_ids)])
    logger.info("Indexing semantic passages for documents %s", document_ids)
    call_command("index_semantic", *args)


def _passage_model():
    return apps.get_model("core", "DocumentPassage")
