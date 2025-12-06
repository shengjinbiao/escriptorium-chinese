from django.core.management.base import BaseCommand, CommandError

from core.models import DocumentPart, Transcription
from knowledge.services.entity_annotation import annotate_part_entities
from knowledge.services.entity_extraction import HanLPModelNotReady, HanLPNotInstalled


class Command(BaseCommand):
    help = "Annotate a document part with HanLP-extracted entities stored as text annotations."

    def add_arguments(self, parser):
        parser.add_argument("--part", type=int, required=True, help="DocumentPart primary key.")
        parser.add_argument(
            "--transcription-id",
            type=int,
            help="Transcription primary key. Defaults to document's manual transcription.",
        )
        parser.add_argument(
            "--transcription-name",
            type=str,
            help="Transcription name (e.g. 'manual'). Ignored if --transcription-id is provided.",
        )
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Keep existing AI annotations instead of replacing them.",
        )

    def handle(self, *args, **options):
        try:
            part = DocumentPart.objects.select_related("document").get(pk=options["part"])
        except DocumentPart.DoesNotExist as exc:
            raise CommandError(f"DocumentPart {options['part']} not found.") from exc

        transcription = self._resolve_transcription(part, options)
        if transcription is None:
            raise CommandError("No transcription found for the provided options.")

        try:
            created = annotate_part_entities(
                part=part,
                transcription=transcription,
                clear_existing=not options["keep"],
            )
        except HanLPNotInstalled as exc:
            raise CommandError(str(exc)) from exc
        except HanLPModelNotReady as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Annotated part #{part.pk} ({part}) with {created} entity spans on transcription '{transcription.name}'."
            )
        )

    def _resolve_transcription(self, part, options):
        transcription_id = options.get("transcription_id")
        transcription_name = options.get("transcription_name")

        if transcription_id:
            try:
                return Transcription.objects.get(pk=transcription_id, document=part.document)
            except Transcription.DoesNotExist:
                raise CommandError(f"Transcription {transcription_id} does not belong to document {part.document_id}.")

        if transcription_name:
            try:
                return part.document.transcriptions.get(name=transcription_name)
            except Transcription.DoesNotExist:
                raise CommandError(
                    f"Transcription named '{transcription_name}' not found on document {part.document_id}."
                )

        return part.document.transcriptions.filter(name=Transcription.DEFAULT_NAME).first()
