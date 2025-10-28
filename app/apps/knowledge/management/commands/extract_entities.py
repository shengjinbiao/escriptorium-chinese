import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from knowledge.services.entity_extraction import (
    HanLPEntityExtractor,
    HanLPModelNotReady,
    HanLPNotInstalled,
)


class Command(BaseCommand):
    help = "Run HanLP entity extraction on supplied text to verify pipeline output."

    def add_arguments(self, parser):
        parser.add_argument(
            "--text",
            type=str,
            help="Raw text to analyse. Mutual exclusive with --file.",
        )
        parser.add_argument(
            "--file",
            type=str,
            help="Path to a UTF-8 text file to analyse.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit JSON instead of plain text output.",
        )

    def handle(self, *args, **options):
        text = options.get("text")
        file_path = options.get("file")

        if text and file_path:
            raise CommandError("Provide either --text or --file, not both.")

        if file_path:
            path = Path(file_path)
            if not path.exists():
                raise CommandError(f"File not found: {file_path}")
            text = path.read_text(encoding="utf-8")

        if not text:
            raise CommandError("No text supplied. Use --text or --file to provide input.")

        try:
            extractor = HanLPEntityExtractor()
        except HanLPNotInstalled as exc:
            raise CommandError(str(exc)) from exc

        try:
            spans = extractor.extract(text)
        except HanLPModelNotReady as exc:
            raise CommandError(str(exc)) from exc

        if options.get("json"):
            payload = [
                {
                    "text": span.text,
                    "label": span.label,
                    "start_char": span.start_char,
                    "end_char": span.end_char,
                    "attributes": span.attributes,
                }
                for span in spans
            ]
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            if not spans:
                self.stdout.write(self.style.WARNING("No entities found in the supplied text."))
                return
            for span in spans:
                attrs = ", ".join(f"{key}: {value}" for key, value in span.attributes.items()) or "—"
                self.stdout.write(
                    f"{span.label:>10} | {span.text} | offset=({span.start_char}, {span.end_char}) | attrs={attrs}"
                )
