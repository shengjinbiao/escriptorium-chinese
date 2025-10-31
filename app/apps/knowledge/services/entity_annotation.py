from __future__ import annotations

import json
from typing import Dict, Optional, Tuple

from django.db import transaction

from core.models import (
    AnnotationComponent,
    AnnotationTaxonomy,
    AnnotationType,
    DocumentPart,
    LineTranscription,
    NAMED_ENTITY_DEFAULT_TYPES,
    TextAnnotation,
    TextAnnotationComponentValue,
    Transcription,
)

from knowledge.services.entity_extraction import EntitySpan, HanLPEntityExtractor

ENTITY_LABEL_DISPLAY = {
    "PERSON": "Person",
    "PER": "Person",
    "NR": "Person",
    "LOC": "Location",
    "NS": "Location",
    "LOCATION": "Location",
    "PLACE": "Place",
    "GPE": "Location",
    "ORG": "Organization",
    "TIME": "Time",
    "DATE": "Date",
    "ERA_DATE": "Era Date",
    "DYNASTY": "Dynasty",
    "EVENT": "Event",
}

COMPONENT_SPECS = {
    "Entity Type": NAMED_ENTITY_DEFAULT_TYPES,
    "Normalized Value": None,
    "Attributes": None,
    "Confidence": None,
}

ENTITY_TYPE_PRIORITY = {
    value: index for index, value in enumerate(NAMED_ENTITY_DEFAULT_TYPES)
}


def _resolve_entity_type(span: EntitySpan) -> str:
    label = (span.label or "").upper()
    type_value = ENTITY_LABEL_DISPLAY.get(label, span.label.title() if span.label else "Other")
    if type_value not in NAMED_ENTITY_DEFAULT_TYPES:
        type_value = "Other"
    return type_value


def _coerce_confidence(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ensure_ai_taxonomy(document) -> (AnnotationTaxonomy, Dict[str, AnnotationComponent]):
    """
    Ensure a dedicated taxonomy for AI generated entity annotations exists on the document.
    Returns the taxonomy and a mapping of component name -> component instance.
    """
    components: Dict[str, AnnotationComponent] = {}
    for name, allowed in COMPONENT_SPECS.items():
        defaults = {"allowed_values": allowed}
        component, created = AnnotationComponent.objects.get_or_create(
            document=document,
            name=name,
            defaults=defaults,
        )
        if not created and component.allowed_values != allowed:
            component.allowed_values = allowed
            component.save(update_fields=["allowed_values"])
        components[name] = component

    annotation_type, _ = AnnotationType.objects.get_or_create(
        name="Named Entity",
        defaults={"public": True, "default": True},
    )

    taxonomy_defaults = {
        "typology": annotation_type,
        "has_comments": False,
        "abbreviation": "AI",
        "marker_type": AnnotationTaxonomy.MARKER_TYPE_BG_COLOR,
        "marker_detail": "#facc15",
    }
    taxonomy, created = AnnotationTaxonomy.objects.get_or_create(
        document=document,
        name="Named Entity (AI)",
        defaults=taxonomy_defaults,
    )
    if created:
        taxonomy.components.set(components.values())
    else:
        taxonomy.components.add(*components.values())

    return taxonomy, components


def annotate_part_entities(
    part: DocumentPart,
    transcription: Transcription,
    extractor: Optional[HanLPEntityExtractor] = None,
    clear_existing: bool = True,
) -> int:
    """
    Run HanLP extraction on all lines of a document part and store results as TextAnnotations.

    Returns the number of annotations created.
    """
    taxonomy, components = ensure_ai_taxonomy(part.document)
    extractor = extractor or HanLPEntityExtractor()

    line_qs = (
        LineTranscription.objects.filter(line__document_part=part, transcription=transcription)
        .select_related("line")
        .order_by("line__order")
    )

    if not line_qs.exists():
        return 0

    with transaction.atomic():
        if clear_existing:
            TextAnnotation.objects.filter(
                part=part,
                transcription=transcription,
                taxonomy=taxonomy,
            ).delete()

        created = 0
        for line_trans in line_qs:
            text = line_trans.text or ""
            if not text.strip():
                continue
            spans = extractor.extract(text)

            merged: Dict[Tuple[int, int], Dict[str, object]] = {}
            for span in spans:
                start_offset = max(0, span.start_char)
                end_offset = min(len(text), span.end_char)
                if end_offset <= start_offset:
                    continue

                type_value = _resolve_entity_type(span)
                attributes_raw = span.attributes or {}
                attributes_value = dict(attributes_raw)
                if span.label and type_value.lower() != (span.label or "").lower():
                    attributes_value.setdefault("original_label", span.label)
                confidence_float = _coerce_confidence(attributes_value.get("confidence"))
                confidence_score = confidence_float if confidence_float is not None else float("-inf")
                key = (start_offset, end_offset)
                candidate = {
                    "type": type_value,
                    "text": span.text,
                    "attributes": attributes_value,
                    "confidence_value": confidence_float,
                    "confidence_score": confidence_score,
                    "start": start_offset,
                    "end": end_offset,
                }
                existing = merged.get(key)
                if existing:
                    if confidence_score > existing["confidence_score"]:
                        merged[key] = candidate
                    elif confidence_score == existing["confidence_score"]:
                        if ENTITY_TYPE_PRIORITY.get(
                            type_value,
                            len(NAMED_ENTITY_DEFAULT_TYPES),
                        ) < ENTITY_TYPE_PRIORITY.get(
                            existing["type"],
                            len(NAMED_ENTITY_DEFAULT_TYPES),
                        ):
                            merged[key] = candidate
                    continue
                merged[key] = candidate

            for record in sorted(merged.values(), key=lambda item: item["start"]):
                annotation = TextAnnotation.objects.create(
                    taxonomy=taxonomy,
                    part=part,
                    start_line=line_trans.line,
                    start_offset=record["start"],
                    end_line=line_trans.line,
                    end_offset=record["end"],
                    transcription=transcription,
                    comments=[],
                )
                _assign_components(annotation, components, record)
                created += 1

    return created


def _assign_components(
    annotation: TextAnnotation,
    components: Dict[str, AnnotationComponent],
    record: Dict[str, object],
) -> None:
    type_value = record.get("type") or "Other"
    text_value = (record.get("text") or "")[:256]
    attributes_value = record.get("attributes") or {}
    confidence_value = record.get("confidence_value")

    TextAnnotationComponentValue.objects.create(
        component=components["Entity Type"],
        annotation=annotation,
        value=type_value,
    )

    TextAnnotationComponentValue.objects.create(
        component=components["Normalized Value"],
        annotation=annotation,
        value=text_value,
    )

    if attributes_value:
        TextAnnotationComponentValue.objects.create(
            component=components["Attributes"],
            annotation=annotation,
            value=json.dumps(attributes_value, ensure_ascii=False)[:256],
        )

    if confidence_value is not None:
        TextAnnotationComponentValue.objects.create(
            component=components["Confidence"],
            annotation=annotation,
            value=f"{float(confidence_value):.3f}",
        )
