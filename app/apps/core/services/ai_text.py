"""
Utilities for running AI-based punctuation and translation on document parts.
"""

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model

from versioning.models import NoChangeException

try:  # typing support without triggering imports
    from typing import TYPE_CHECKING
except ImportError:  # pragma: no cover
    TYPE_CHECKING = False

if TYPE_CHECKING:  # pragma: no cover
    from core.models import DocumentPart, Line, LineTranscription, Transcription

logger = logging.getLogger(__name__)

User = get_user_model()

try:
    from wz_gazetteer.services.openai_client import (
        OpenAIClient,
        ProviderConfig,
        load_provider_config,
    )
    from wz_gazetteer.services.punctuation import PunctuationService
    from wz_gazetteer.services.translation import TranslationResult, TranslationService
    from wz_gazetteer.utilities.cache import JsonCache

    _GAZETTEER_IMPORT_ERROR: Optional[Exception] = None
except ImportError as exc:  # pragma: no cover - handled at runtime
    PunctuationService = TranslationService = None  # type: ignore[assignment]
    OpenAIClient = ProviderConfig = JsonCache = None  # type: ignore[assignment]
    load_provider_config = None  # type: ignore[assignment]
    TranslationResult = None  # type: ignore[assignment]
    _GAZETTEER_IMPORT_ERROR = exc

_punctuation_service: Optional[PunctuationService] = None
_translation_service: Optional[TranslationService] = None
_provider_config: Optional[ProviderConfig] = None


def _line_model():
    return apps.get_model("core", "Line")


def _line_transcription_model():
    return apps.get_model("core", "LineTranscription")


def _transcription_model():
    return apps.get_model("core", "Transcription")


class AIDependencyError(RuntimeError):
    """Raised when the AI helper dependencies are missing."""


@dataclass(frozen=True)
class AIOperations:
    punctuate: bool = True
    translate: bool = True

    def has_work(self) -> bool:
        return self.punctuate or self.translate

    @classmethod
    def from_payload(cls, payload: Optional[dict]) -> "AIOperations":
        if not payload:
            return cls()
        return cls(
            punctuate=bool(payload.get("punctuate", True)),
            translate=bool(payload.get("translate", True)),
        )


def _ensure_dependencies() -> None:
    if _GAZETTEER_IMPORT_ERROR is not None:
        raise AIDependencyError(
            "wz-gazetteer package is not available. "
            "Install it (e.g. `pip install -e ../yjxz`) inside the eScriptorium environment."
        ) from _GAZETTEER_IMPORT_ERROR


def _ensure_provider_config() -> ProviderConfig:
    global _provider_config
    if _provider_config is not None:
        return _provider_config

    if load_provider_config is None:
        _ensure_dependencies()
        raise AssertionError("load_provider_config unexpectedly missing")

    config_path = Path(settings.AI_PROVIDER_CONFIG_PATH)
    if not config_path.exists():
        raise FileNotFoundError(
            f"AI provider configuration file not found: {config_path}"
        )
    _provider_config = load_provider_config(config_path)
    return _provider_config


def _build_cache(path_name: str) -> JsonCache:
    cache_root = Path(settings.AI_CACHE_ROOT)
    cache_root.mkdir(parents=True, exist_ok=True)
    return JsonCache(cache_root / path_name)


def get_punctuation_service() -> PunctuationService:
    _ensure_dependencies()
    global _punctuation_service
    if _punctuation_service is None:
        config = _ensure_provider_config()
        client = OpenAIClient(config)
        _punctuation_service = PunctuationService(client, _build_cache("punctuation_cache.json"))
    return _punctuation_service


def get_translation_service() -> TranslationService:
    _ensure_dependencies()
    global _translation_service
    if _translation_service is None:
        config = _ensure_provider_config()
        client = OpenAIClient(config)
        _translation_service = TranslationService(client, _build_cache("translation_cache.json"))
    return _translation_service


def _get_source_transcription(document) -> Optional[Transcription]:
    Transcription = _transcription_model()
    LineTranscription = _line_transcription_model()

    ai_names = {
        name
        for name in (
            settings.AI_PUNCTUATION_TRANSCRIPTION_NAME,
            settings.AI_TRANSLATION_TRANSCRIPTION_NAME,
        )
        if name
    }

    latest_line = (
        LineTranscription.objects.filter(
            transcription__document=document,
            transcription__archived=False,
        )
        .exclude(transcription__name__in=ai_names)
        .select_related("transcription")
        .order_by("-version_updated_at")
        .first()
    )
    if latest_line:
        return latest_line.transcription

    fallback_qs = (
        Transcription.objects.filter(document=document, archived=False)
        .exclude(name__in=ai_names)
        .order_by("-updated_at", "pk")
    )
    transcription = fallback_qs.first()
    if transcription:
        return transcription

    return (
        Transcription.objects.filter(document=document, archived=False)
        .order_by("-updated_at", "pk")
        .first()
    )


def _get_destination_transcription(document, name: str) -> Transcription:
    Transcription = _transcription_model()
    transcription, created = Transcription.objects.get_or_create(
        document=document,
        name=name,
        defaults={
            "comments": "Auto-generated by AI tools.",
            "archived": False,
        },
    )
    if not created and transcription.archived:
        transcription.archived = False
        transcription.save(update_fields=["archived"])
    return transcription


def _collect_line_text(
    lines: Iterable[Line],
    transcription: Transcription,
) -> List[str]:
    results: List[str] = []
    LineTranscription = _line_transcription_model()
    for line in lines:
        entry = (
            LineTranscription.objects.filter(
                line=line,
                transcription=transcription,
            )
            .only("content")
            .first()
        )
        results.append(entry.content if entry and entry.content else "")
    return results


_PUNCTUATION_EXTRA = frozenset(
    "，。！？；：、．,.!?;:()（）《》〈〉「」『』“”‘’—…·﹔﹕﹖﹗"
)


def _get_neighbor_line_content(
    part: "DocumentPart",
    transcription: "Transcription",
    *,
    direction: str,
) -> Optional[str]:
    Line = _line_model()
    if direction == "previous":
        queryset = (
            Line.objects.filter(
                document_part__document=part.document,
                document_part__order__lt=part.order,
            )
            .order_by("-document_part__order", "-order")
            .only("pk")
        )
    else:
        queryset = (
            Line.objects.filter(
                document_part__document=part.document,
                document_part__order__gt=part.order,
            )
            .order_by("document_part__order", "order")
            .only("pk")
        )
    neighbor = queryset.first()
    if neighbor is None:
        return None

    LineTranscription = _line_transcription_model()
    entry = (
        LineTranscription.objects.filter(
            line=neighbor,
            transcription=transcription,
        )
        .only("content")
        .first()
    )
    if not entry or not entry.content:
        return None
    return entry.content


def _build_context_lines(
    part: "DocumentPart",
    transcription: "Transcription",
    *,
    include_before: bool,
    include_after: bool,
) -> Tuple[Optional[str], Optional[str]]:
    before = (
        _get_neighbor_line_content(part, transcription, direction="previous")
        if include_before
        else None
    )
    after = (
        _get_neighbor_line_content(part, transcription, direction="next")
        if include_after
        else None
    )
    return before, after


def _is_punctuation_char(ch: str) -> bool:
    if ch in _PUNCTUATION_EXTRA:
        return True
    category = unicodedata.category(ch)
    return category.startswith("P")


def _strip_core_text(text: str) -> str:
    return "".join(
        ch for ch in text if not _is_punctuation_char(ch) and not ch.isspace()
    )


def _merge_punctuation_text(
    original_lines: Sequence[str],
    candidate_text: str,
) -> List[str]:
    if not candidate_text.strip():
        return list(original_lines)

    original_text = "\n".join(original_lines)
    orig_chars = list(original_text)
    result: List[str] = []
    punct_buffer: List[str] = []

    def flush_buffer() -> None:
        if punct_buffer:
            result.append("".join(punct_buffer))
            punct_buffer.clear()

    idx = 0
    started = False
    candidate_iter = iter(candidate_text)
    for ch in candidate_iter:
        if ch == "\r":
            continue
        if idx >= len(orig_chars):
            break

        if not started:
            if ch.isspace() and ch != "\n":
                continue
            if _is_punctuation_char(ch):
                continue
            remaining = "".join(orig_chars[idx:])
            forward_idx = remaining.find(ch)
            if forward_idx < 0:
                continue
            started = True
            flush_buffer()
            skip_until = idx + forward_idx
            while idx < skip_until:
                result.append(orig_chars[idx])
                idx += 1
            result.append(orig_chars[idx])
            idx += 1
            continue

        if ch.isspace() and ch != "\n":
            continue

        if idx < len(orig_chars) and ch == orig_chars[idx]:
            flush_buffer()
            result.append(ch)
            idx += 1
            continue

        if ch == "\n":
            if idx < len(orig_chars) and orig_chars[idx] == "\n":
                flush_buffer()
                result.append(ch)
                idx += 1
            continue

        if _is_punctuation_char(ch):
            punct_buffer.append(ch)
            continue

        if idx < len(orig_chars):
            remaining = "".join(orig_chars[idx:])
            forward_idx = remaining.find(ch)
            if forward_idx >= 0:
                flush_buffer()
                skip_until = idx + forward_idx
                while idx < skip_until:
                    result.append(orig_chars[idx])
                    idx += 1
                result.append(orig_chars[idx])
                idx += 1
                continue
        # Drop non-punctuation characters that cannot be aligned to the source text.
        continue

    flush_buffer()

    while idx < len(orig_chars):
        result.append(orig_chars[idx])
        idx += 1

    merged_text = "".join(result)
    if _strip_core_text(merged_text) != _strip_core_text(original_text):
        return list(original_lines)

    merged_lines = merged_text.split("\n")
    if len(merged_lines) < len(original_lines):
        merged_lines.extend([""] * (len(original_lines) - len(merged_lines)))
    elif len(merged_lines) > len(original_lines):
        merged_lines = merged_lines[: len(original_lines)]
    return merged_lines


def _call_punctuate_with_context(
    service: PunctuationService,
    text: str,
    *,
    context_before: Optional[str],
    context_after: Optional[str],
) -> str:
    try:
        return service.punctuate(
            text,
            context_before=context_before,
            context_after=context_after,
        )
    except TypeError as exc:
        message = str(exc)
        if "context_before" in message or "context_after" in message:
            return service.punctuate(text)
        raise


def _call_translate_with_context(
    service: TranslationService,
    text: str,
    *,
    context_before: Optional[str],
    context_after: Optional[str],
) -> TranslationResult:
    try:
        return service.translate(
            text,
            context_before=context_before,
            context_after=context_after,
        )
    except TypeError as exc:
        message = str(exc)
        if "context_before" in message or "context_after" in message:
            return service.translate(text)
        raise


def _align_result_lines(result_lines: List[str], target_count: int) -> List[str]:
    if len(result_lines) == target_count:
        return result_lines
    if not result_lines:
        return [""] * target_count
    if len(result_lines) < target_count:
        return result_lines + [""] * (target_count - len(result_lines))
    aligned = result_lines[: max(target_count - 1, 0)]
    aligned.append("\n".join(result_lines[len(aligned) :]))
    return aligned[:target_count]


def _write_line_contents(
    *,
    lines: Iterable[Line],
    transcription: Transcription,
    values: List[str],
    user: Optional[User],
    source_label: str,
) -> int:
    updated = 0
    username = getattr(user, "username", None) or source_label
    LineTranscription = _line_transcription_model()
    for line, content in zip(lines, values):
        lt, created = LineTranscription.objects.get_or_create(
            line=line,
            transcription=transcription,
            defaults={
                "content": content,
                "version_author": username,
                "version_source": source_label,
            },
        )
        if created:
            updated += 1 if content else 0
            continue
        if lt.content == content:
            continue
        try:
            lt.new_version(author=username, source=source_label)
        except NoChangeException:
            pass
        lt.content = content
        lt.version_author = username
        lt.version_source = source_label
        lt.avg_confidence = None
        lt.save()
        updated += 1
    return updated


def enrich_document_part(
    part: DocumentPart,
    operations: AIOperations,
    *,
    user: Optional[User] = None,
    include_previous_context: bool = False,
    include_next_context: bool = False,
) -> dict:
    """
    Run punctuation and/or translation on a document part and update AI layers.
    """

    if not operations.has_work():
        return {
            "part_id": part.pk,
            "status": "skipped",
            "reason": "no_operations_requested",
        }

    Line = _line_model()
    lines = list(Line.objects.filter(document_part=part).order_by("order"))
    if not lines:
        return {
            "part_id": part.pk,
            "status": "skipped",
            "reason": "no_lines",
        }

    source_transcription = _get_source_transcription(part.document)
    if source_transcription is None:
        raise RuntimeError(
            f"Document {part.document_id} has no available transcription to read from."
        )

    line_texts = _collect_line_text(lines, source_transcription)
    if not any(text.strip() for text in line_texts):
        return {
            "part_id": part.pk,
            "status": "skipped",
            "reason": "empty_source",
        }

    joined_text = "\n".join(line_texts)
    result: dict = {"part_id": part.pk, "status": "ok"}
    context_before: Optional[str] = None
    context_after: Optional[str] = None

    if include_previous_context or include_next_context:
        context_before, context_after = _build_context_lines(
            part,
            source_transcription,
            include_before=include_previous_context,
            include_after=include_next_context,
        )

    if operations.punctuate:
        service = get_punctuation_service()
        punctuated = _call_punctuate_with_context(
            service,
            joined_text,
            context_before=context_before,
            context_after=context_after,
        )
        punctuated_lines = _merge_punctuation_text(line_texts, punctuated)
        ai_transcription = _get_destination_transcription(
            part.document,
            settings.AI_PUNCTUATION_TRANSCRIPTION_NAME,
        )
        result["punctuation_updated"] = _write_line_contents(
            lines=lines,
            transcription=ai_transcription,
            values=punctuated_lines,
            user=user,
            source_label="ai_punctuation",
        )

    if operations.translate:
        service = get_translation_service()
        translation: TranslationResult = _call_translate_with_context(
            service,
            joined_text,
            context_before=context_before,
            context_after=context_after,
        )
        translation_lines = _align_result_lines(
            translation.text.splitlines(), len(lines)
        )
        ai_transcription = _get_destination_transcription(
            part.document,
            settings.AI_TRANSLATION_TRANSCRIPTION_NAME,
        )
        result["translation_updated"] = _write_line_contents(
            lines=lines,
            transcription=ai_transcription,
            values=translation_lines,
            user=user,
            source_label=f"ai_translation:{translation.provider}",
        )

    return result
