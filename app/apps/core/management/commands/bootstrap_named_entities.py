from django.core.management.base import BaseCommand, CommandError

from core.models import Document


class Command(BaseCommand):
    help = "Ensure the default Named Entity annotation taxonomy exists on all documents."

    def add_arguments(self, parser):
        parser.add_argument(
            "--document-id",
            type=int,
            dest="document_id",
            help="Limit bootstrap to a single document ID.",
        )

    def handle(self, *args, **options):
        document_id = options.get("document_id")
        queryset = Document.objects.all()
        if document_id is not None:
            queryset = queryset.filter(pk=document_id)
            if not queryset.exists():
                raise CommandError(f"Document with id={document_id} does not exist.")

        processed = 0
        for document in queryset.iterator():
            document._bootstrap_named_entity_annotations()
            processed += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {processed} document(s)."))
