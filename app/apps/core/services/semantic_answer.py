"""Utilities to generate semantic QA answers combining search hits and LLM output."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from django.conf import settings

from core.services.embedding import EmbeddingServiceNotConfigured
from core.services.semantic_search import semantic_search

logger = logging.getLogger(__name__)


try:  # noqa: SIM105 - optional dependency
    from wz_gazetteer.services.openai_client import (  # type: ignore
        OpenAIClient,
        ProviderConfig,
        load_provider_config,
    )
except ImportError as exc:  # pragma: no cover - handled at runtime
    OpenAIClient = None  # type: ignore[assignment]
    load_provider_config = None  # type: ignore[assignment]
    _QA_IMPORT_ERROR: Optional[Exception] = exc
else:
    _QA_IMPORT_ERROR = None


class SemanticAnswerNotConfigured(RuntimeError):
    """Raised when the QA stack cannot be initialised."""


_qa_client: Optional[OpenAIClient] = None


def _get_qa_client() -> OpenAIClient:
    if OpenAIClient is None or load_provider_config is None:
        raise SemanticAnswerNotConfigured(
            "OpenAI client is not available. Install the wz-gazetteer package."
        ) from _QA_IMPORT_ERROR

    global _qa_client
    if _qa_client is not None:
        return _qa_client

    config_path = Path(settings.AI_PROVIDER_CONFIG_PATH)
    if not config_path.exists():
        raise SemanticAnswerNotConfigured(
            f"AI provider configuration file not found: {config_path}"
        )

    try:
        config: ProviderConfig = load_provider_config(config_path)
    except Exception as exc:  # noqa: BLE001
        raise SemanticAnswerNotConfigured(str(exc)) from exc

    _qa_client = OpenAIClient(config)
    return _qa_client


@dataclass
class SemanticAnswer:
    text: str
    citations: List[Dict[str, object]]


def build_semantic_answer(
    query: str,
    *,
    limit: int = 5,
    documents: Optional[Iterable[int]] = None,
    document_parts: Optional[Iterable[int]] = None,
    with_answer: bool = True,
) -> Dict[str, object]:
    """Return semantic hits and, optionally, a generated answer."""

    hits_payload = semantic_search(
        query,
        limit=limit,
        documents=documents,
        document_parts=document_parts,
    )

    hits = hits_payload.get("hits", [])
    response: Dict[str, object] = {"hits": hits}

    if not with_answer:
        return response

    if not query.strip():
        response["answer"] = {
            "text": "",
            "citations": [],
        }
        return response

    if not hits:
        response["answer"] = {
            "text": "暂无相关资料。",
            "citations": [],
        }
        return response

    try:
        client = _get_qa_client()
    except SemanticAnswerNotConfigured as exc:
        response["error"] = str(exc)
        return response

    context_blocks: List[str] = []
    citations: List[Dict[str, object]] = []

    for idx, hit in enumerate(hits[: limit or 5], start=1):
        meta = hit.get("metadata") or {}
        text = (hit.get("text") or "").strip()
        snippet = text.replace("\n", " ")
        if len(snippet) > 160:
            snippet = snippet[:160] + "…"

        title = meta.get("document_part_title") or ""
        heading = title or "段落"
        context_blocks.append(f"[{idx}] {heading}\n{snippet}")
        citations.append(
            {
                "number": idx,
                "document_id": hit.get("document_id"),
                "document_part_id": hit.get("document_part_id"),
                "score": hit.get("score"),
                "title": title,
                "text": snippet,
            }
        )

    context = "\n\n".join(context_blocks)

    messages = [
        {"role": "system", "content": client.config.qa_prompt},
        {
            "role": "user",
            "content": (
                "问题：" + query + "\n\n"
                "参考资料：\n" + context + "\n\n"
                "请基于以上资料回答，并引用对应编号（如 [1][2]）。若资料不足，请说明。"
            ),
        },
    ]

    try:
        answer_text = client.chat_completion(
            model=client.config.qa_model,
            messages=messages,
            temperature=0.2,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Semantic answer generation failed")
        response["error"] = str(exc)
        return response

    response["answer"] = SemanticAnswer(text=answer_text, citations=citations).__dict__
    return response
