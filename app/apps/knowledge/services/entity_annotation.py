from __future__ import annotations

import json
from typing import Dict, Optional

from django.db import transaction

from core.models import (
    AnnotationComponent,
    AnnotationTaxonomy,
    AnnotationType,
    DocumentPart,
    LineTranscription,
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
}

COMPONENT_SPECS = {
    "Entity Type": ["Person", "Location", "Organization", "Time", "Date", "Era Date", "Dynasty", "Place", "Other"],
    "Normalized Value": None,
    "Attributes": None,
    "Confidence": None,
}


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
            text = line_trans.text
            if not text:
                continue
            spans = extractor.extract(text)

            for span in spans:
                start_offset = max(0, span.start_char)
                end_offset = min(len(text), span.end_char)
                if end_offset <= start_offset:
                    continue

                annotation = TextAnnotation.objects.create(
                    taxonomy=taxonomy,
                    part=part,
                    start_line=line_trans.line,
                    start_offset=start_offset,
                    end_line=line_trans.line,
                    end_offset=end_offset,
                    transcription=transcription,
                    comments=[],
                )
                _assign_components(annotation, components, span)
                created += 1

    return created


def _assign_components(
    annotation: TextAnnotation,
    components: Dict[str, AnnotationComponent],
    span: EntitySpan,
) -> None:
    type_value = ENTITY_LABEL_DISPLAY.get(span.label.upper(), span.label.title())
    attributes_value = span.attributes or {}
    confidence = attributes_value.get("confidence")

    TextAnnotationComponentValue.objects.create(
        component=components["Entity Type"],
        annotation=annotation,
        value=type_value,
    )

    TextAnnotationComponentValue.objects.create(
        component=components["Normalized Value"],
        annotation=annotation,
        value=span.text[:256],
    )

    if attributes_value:
        TextAnnotationComponentValue.objects.create(
            component=components["Attributes"],
            annotation=annotation,
            value=json.dumps(attributes_value, ensure_ascii=False)[:256],
        )

    if confidence is not None:
        TextAnnotationComponentValue.objects.create(
            component=components["Confidence"],
            annotation=annotation,
            value=f"{float(confidence):.3f}",
        )
