import itertools
import re

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Prefetch

from core.models import (
    Document,
    DocumentPassage,
    DocumentPart,
    LineTranscription,
    Transcription,
)


def _normalize(text: str) -> str:
    """Collapse whitespace in a passage for embedding-friendly normalization."""

    return re.sub(r"\s+", " ", text or "").strip()


class Command(BaseCommand):
    help = "Generate DocumentPassage records from existing line transcriptions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--documents",
            nargs="+",
            type=int,
            help="Restrict processing to specific document primary keys.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove existing passages for the target documents before regenerating.",
        )
        parser.add_argument(
            "--min-chars",
            type=int,
            default=20,
            help="Skip passages whose raw text is shorter than this threshold.",
        )

    def handle(self, *args, **options):
        document_ids = options.get("documents")
        reset = options.get("reset")
        min_chars = options.get("min_chars")

        documents = Document.objects.all().order_by("pk")
        if document_ids:
            documents = documents.filter(pk__in=document_ids)

        documents = documents.prefetch_related(
            Prefetch("parts", queryset=DocumentPart.objects.order_by("order"))
        )

        total_passages = 0
        for document in documents:
            with transaction.atomic():
                if reset:
                    DocumentPassage.objects.filter(document=document).delete()

                transcription = self._choose_transcription(document)
                if transcription is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Document {document.pk} has no transcriptions; skipping."
                        )
                    )
                    continue

                lines = (
                    LineTranscription.objects.filter(
                        transcription=transcription,
                        line__document_part__document=document,
                    )
                    .select_related("line", "line__document_part")
                    .order_by("line__document_part__order", "line__order")
                )

                by_part = itertools.groupby(
                    lines, key=lambda lt: lt.line.document_part
                )

                order_counter = (
                    DocumentPassage.objects.filter(document=document)
                    .order_by("-order")
                    .values_list("order", flat=True)
                    .first()
                    or 0
                )

                created_here = 0
                for part, group in by_part:
                    raw_text = "\n".join(
                        lt.content.strip() for lt in group if lt.content
                    ).strip()
                    if len(raw_text) < min_chars:
                        continue

                    order_counter += 1
                    DocumentPassage.objects.create(
                        document=document,
                        document_part=part,
                        order=order_counter,
                        raw_text=raw_text,
                        normalized_text=_normalize(raw_text),
                        metadata={
                            "document_part_id": part.pk if part else None,
                            "document_part_title": getattr(part, "title", None),
                            "document_part_order": getattr(part, "order", None),
                            "transcription_id": transcription.pk,
                            "transcription_name": transcription.name,
                        },
                    )
                    created_here += 1

                total_passages += created_here
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Document {document.pk} → created {created_here} passages."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"Finished. Created {total_passages} passages total.")
        )

    def _choose_transcription(self, document: Document):
        """
        Pick an appropriate transcription layer for passage extraction.
        Prefers the default/manual layer, falls back to the first available.
        """

        manual = document.transcriptions.filter(
            name=Transcription.DEFAULT_NAME
        ).first()
        if manual:
            return manual
        return document.transcriptions.order_by("pk").first()
