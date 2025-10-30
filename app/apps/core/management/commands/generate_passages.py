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

                transcriptions = self._candidate_transcriptions(document)
                if not transcriptions:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Document {document.pk} has no transcriptions; skipping."
                        )
                    )
                    continue

                order_counter = (
                    DocumentPassage.objects.filter(document=document)
                    .order_by("-order")
                    .values_list("order", flat=True)
                    .first()
                    or 0
                )

                created_in_document = 0
                for transcription in transcriptions:
                    lines = (
                        LineTranscription.objects.filter(
                            transcription=transcription,
                            line__document_part__document=document,
                        )
                        .select_related("line", "line__document_part")
                        .order_by("line__document_part__order", "line__order")
                    )

                    if not lines.exists():
                        continue

                    created_in_transcription = 0
                    by_part = itertools.groupby(
                        lines, key=lambda lt: lt.line.document_part
                    )

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
                        created_in_transcription += 1

                    if created_in_transcription == 0:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Document {document.pk} / transcription {transcription.name} produced 0 passages."
                            )
                        )
                    created_in_document += created_in_transcription

                total_passages += created_in_document
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Document {document.pk} → created {created_in_document} passages."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"Finished. Created {total_passages} passages total.")
        )

    def _candidate_transcriptions(self, document: Document):
        """
        Return a prioritized list of transcription layers for passage extraction.
        Prefers the manual layer, then all remaining non-archived transcriptions.
        """

        transcription_qs = (
            document.transcriptions.filter(archived=False)
            .order_by("pk")
            .select_related(None)
        )

        transcriptions = list(transcription_qs)
        manual = next(
            (t for t in transcriptions if t.name == Transcription.DEFAULT_NAME),
            None,
        )
        remaining = [
            t for t in transcriptions if manual is None or t.pk != manual.pk
        ]

        candidates = []
        if manual:
            candidates.append(manual)
        candidates.extend(remaining)
        return candidates
