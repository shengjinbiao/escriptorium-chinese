from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import hanlp  # type: ignore
except ImportError:  # pragma: no cover - dependency optional in some environments
    hanlp = None  # type: ignore

if hanlp:
    MODEL_ID = getattr(
        hanlp.pretrained.mtl,
        "CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH",
        None,
    )
else:
    MODEL_ID = None


@dataclass
class EntitySpan:
    text: str
    label: str
    start_char: int
    end_char: int
    attributes: Dict[str, str] = field(default_factory=dict)

_LABEL_NORMALIZATION = {
    "PER": "PERSON",
    "NR": "PERSON",
    "PERSON": "PERSON",
    "NS": "LOCATION",
    "LOC": "LOCATION",
    "LOCATION": "LOCATION",
    "PLACE": "LOCATION",
    "GPE": "LOCATION",
    "ORG": "ORGANIZATION",
    "ORGANIZATION": "ORGANIZATION",
}

_LABEL_PRIORITY = {
    "PERSON": 0,
    "LOCATION": 0,
    "ORGANIZATION": 1,
    "TIME": 2,
    "DATE": 2,
    "ERA_DATE": 2,
    "DYNASTY": 2,
}


class HanLPNotInstalled(RuntimeError):
    """Raised when HanLP is not available in the environment."""


class HanLPModelNotReady(RuntimeError):
    """Raised when HanLP models are missing and need to be downloaded."""


class HanLPEntityExtractor:
    """
    Thin wrapper around HanLP multi-task pipeline providing NER output with
    additional heuristics tailored to gazetteer texts.
    """

    def __init__(self) -> None:
        if hanlp is None:
            raise HanLPNotInstalled(
                "hanlp is not installed. Add 'hanlp' to requirements and ensure the environment has it available."
            )
        self._pipeline = None

    # Lazy load to avoid upfront model cost during Django start
    def _ensure_pipeline(self):
        if self._pipeline is not None:
            return
        try:
            if MODEL_ID:
                self._pipeline = hanlp.load(MODEL_ID)
            else:  # pragma: no cover - fallback when constant missing
                self._pipeline = hanlp.pipeline()
                self._pipeline.append(hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH), output_key="tok/fine")
                self._pipeline.append(
                    hanlp.load(hanlp.pretrained.ner.MSRA_ELECTRA_SMALL_ZH),
                    output_key="ner/msra",
                    input_key="tok/fine",
                )
        except Exception as exc:  # pragma: no cover
            logger.exception("Failed to load HanLP models")
            raise HanLPModelNotReady(
                "HanLP models are not ready. Run hanlp.pretrained.fetch() with network access to download required weights."
            ) from exc

    def extract(self, text: str) -> List[EntitySpan]:
        if not text:
            return []
        self._ensure_pipeline()
        result = self._pipeline(text)
        tokens = result.get("tok/fine") or result.get("tok") or []
        if tokens and isinstance(tokens[0], list):
            tokens = [tok for sent in tokens for tok in sent]
        token_offsets = self._build_char_offsets(text, tokens)

        spans: List[EntitySpan] = []
        for key, entities in result.items():
            if not key.startswith("ner/"):
                continue
            for entity in entities:
                start_idx: Optional[int] = None
                end_idx: Optional[int] = None
                label: Optional[str] = None
                surface_override: Optional[str] = None

                if isinstance(entity, dict):
                    start_idx = entity.get("start") or entity.get("index")
                    end_idx = entity.get("end") or entity.get("index_end") or entity.get("index2")
                    label = entity.get("label") or entity.get("type")
                    surface_override = entity.get("text") or entity.get("word")
                elif isinstance(entity, (list, tuple)):
                    if len(entity) < 3:
                        continue
                    # HanLP 2.x returns [text, label, start, end]; older versions returned [start, end, label].
                    if len(entity) >= 4 and isinstance(entity[2], (int, float)) and isinstance(entity[3], (int, float)):
                        if isinstance(entity[0], str) and not isinstance(entity[2], str):
                            surface_override = entity[0]
                            label = entity[1]
                            start_idx, end_idx = entity[2], entity[3]
                        else:
                            start_idx, end_idx, label = entity[:3]
                    else:
                        start_idx, end_idx, label = entity[:3]
                    if label is not None:
                        label = str(label)

                try:
                    start_idx = int(start_idx) if start_idx is not None else None
                    end_idx = int(end_idx) if end_idx is not None else None
                except (TypeError, ValueError):
                    continue

                if start_idx is None or end_idx is None or label is None:
                    continue
                if start_idx < 0 or end_idx <= 0 or start_idx >= len(token_offsets):
                    continue
                start_char = token_offsets[start_idx][0]
                end_char = token_offsets[end_idx - 1][1]
                surface = surface_override or "".join(tokens[start_idx:end_idx])
                normalized_label = self._normalize_label(label)
                spans.append(
                    EntitySpan(
                        text=surface,
                        label=normalized_label,
                        start_char=start_char,
                        end_char=end_char,
                    )
                )

        return self._merge_duplicates(spans)

    def _normalize_label(self, raw_label: Optional[str]) -> str:
        if raw_label is None:
            return "OTHER"
        upper = str(raw_label).strip().upper()
        if not upper:
            return "OTHER"
        return _LABEL_NORMALIZATION.get(upper, upper)

    def _build_char_offsets(self, text: str, tokens: List[str]) -> List[Tuple[int, int]]:
        offsets: List[Tuple[int, int]] = []
        cursor = 0
        for token in tokens:
            start = text.find(token, cursor)
            if start == -1:
                start = cursor
            end = start + len(token)
            offsets.append((start, end))
            cursor = end
        return offsets

    def _merge_duplicates(self, spans: List[EntitySpan]) -> List[EntitySpan]:
        merged: Dict[Tuple[str, int, int], EntitySpan] = {}
        for span in spans:
            key = (span.text, span.start_char, span.end_char)
            existing = merged.get(key)
            if existing is None:
                merged[key] = span
                continue

            existing_priority = _LABEL_PRIORITY.get(existing.label, 99)
            new_priority = _LABEL_PRIORITY.get(span.label, 99)

            if new_priority < existing_priority:
                span.attributes.update(existing.attributes)
                merged[key] = span
            else:
                existing.attributes.update(span.attributes)

        return list(merged.values())

    def debug_extract(self, text: str) -> str:
        data = [span.__dict__ for span in self.extract(text)]
        return json.dumps(data, ensure_ascii=False, indent=2)
