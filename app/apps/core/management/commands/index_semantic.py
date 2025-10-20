import logging
from math import ceil

from django.conf import settings
from django.core.management.base import BaseCommand

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk as es_bulk

from core.models import DocumentPassage

logger = logging.getLogger("es_indexing")
logger.setLevel(logging.ERROR)


def build_semantic_mapping(dim: int) -> dict:
    return {
        "properties": {
            "document_id": {"type": "long"},
            "document_part_id": {"type": "long"},
            "passage_order": {"type": "integer"},
            "raw_text": {"type": "text", "analyzer": "smartcn"},
            "normalized_text": {"type": "text", "analyzer": "smartcn"},
            "metadata": {"type": "object"},
            "embedding": {
                "type": "dense_vector",
                "dims": dim,
                "index": True,
                "similarity": "cosine",
            },
        }
    }


class Command(BaseCommand):
    help = "Index semantic passages (DocumentPassage) to Elasticsearch."

    def add_arguments(self, parser):
        parser.add_argument(
            "--documents",
            nargs="+",
            type=int,
            help="Only index passages belonging to the specified document primary keys.",
        )
        parser.add_argument(
            "--drop",
            action="store_true",
            help="Drop the existing semantic index before reindexing.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of passages to stream per bulk request.",
        )

    def handle(self, *args, **options):
        if settings.DISABLE_ELASTICSEARCH:
            logger.error(
                "Please set DISABLE_ELASTICSEARCH to 'False' to run semantic indexing."
            )
            return

        index_name = settings.ELASTICSEARCH_SEMANTIC_INDEX
        batch_size = max(10, options["batch_size"])
        document_filter = options.get("documents")

        es_client = Elasticsearch(settings.ELASTICSEARCH_URL)
        if not es_client.ping():
            logger.error(
                "Unable to connect to Elasticsearch host defined as %s.",
                settings.ELASTICSEARCH_URL,
            )
            return

        if options.get("drop"):
            es_client.indices.delete(index=index_name, ignore_unavailable=True)

        if not es_client.indices.exists(index=index_name):
            mapping = build_semantic_mapping(settings.SEMANTIC_EMBEDDING_DIM)
            es_client.indices.create(index=index_name, mappings=mapping)
            logger.info("Created semantic index %s", index_name)

        passages = DocumentPassage.objects.exclude(embedding__isnull=True)
        if document_filter:
            passages = passages.filter(document_id__in=document_filter)
        total = passages.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No passages with embeddings found."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Indexing {total} passages into '{index_name}' with batch size {batch_size}"
            )
        )

        successes = 0

        for offset in range(0, total, batch_size):
            chunk = list(
                passages.order_by("document_id", "order")[offset : offset + batch_size]
            )
            actions = []
            for passage in chunk:
                if not passage.embedding:
                    continue
                actions.append(
                    {
                        "_index": index_name,
                        "_id": passage.pk,
                        "document_id": passage.document_id,
                        "document_part_id": passage.document_part_id,
                        "passage_order": passage.order,
                        "raw_text": passage.raw_text,
                        "normalized_text": passage.normalized_text,
                        "metadata": passage.metadata or {},
                        "embedding": passage.embedding,
                    }
                )

            if not actions:
                continue
            inserted, _ = es_bulk(es_client, actions, stats_only=True)
            successes += inserted
            self.stdout.write(
                f"Indexed {successes}/{total} passages "
                f"({ceil(successes / total * 100)}%)."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed semantic indexing: inserted {successes} documents."
            )
        )
