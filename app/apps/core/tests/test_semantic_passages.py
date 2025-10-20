from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from core.models import DocumentPassage, LineTranscription, Transcription
from core.tasks import generate_passage_embeddings_task
from core.tests.factory import CoreFactory


class DocumentPassageGenerationTests(TestCase):
    def setUp(self):
        self.factory = CoreFactory()

    def tearDown(self):
        self.factory.cleanup()

    def test_generate_passages_creates_records_per_part(self):
        document = self.factory.make_document()
        transcription = document.transcriptions.get(name=Transcription.DEFAULT_NAME)
        part = self.factory.make_part(document=document)
        # create three lines of content tied to the manual transcription
        self.factory.make_content(part, amount=3, transcription=transcription)

        call_command("generate_passages", "--documents", str(document.pk), "--reset")

        passages = DocumentPassage.objects.filter(document=document).order_by("order")
        self.assertEqual(passages.count(), 1)

        passage = passages.first()
        self.assertTrue(passage.raw_text)
        self.assertEqual(passage.metadata["document_part_id"], part.pk)
        self.assertEqual(passage.metadata["transcription_id"], transcription.pk)
        self.assertEqual(passage.order, 1)


class EmbeddingTaskTests(TestCase):
    def setUp(self):
        self.factory = CoreFactory()

    def tearDown(self):
        self.factory.cleanup()

    def test_generate_passage_embeddings_task_handles_empty(self):
        result = generate_passage_embeddings_task([])
        self.assertEqual(result["processed"], 0)

    @patch("core.tasks.generate_embeddings_for_passages")
    def test_generate_passage_embeddings_task_counts_passages(self, mock_generate):
        document = self.factory.make_document()
        transcription = document.transcriptions.get(name=Transcription.DEFAULT_NAME)
        part = self.factory.make_part(document=document)
        self.factory.make_content(part, amount=2, transcription=transcription)

        call_command("generate_passages", "--documents", str(document.pk), "--reset")
        passage_ids = list(DocumentPassage.objects.filter(document=document).values_list("id", flat=True))
        mock_generate.return_value = {
            "processed": len(passage_ids),
            "succeeded": len(passage_ids),
            "failed": 0,
            "model": "stub",
        }

        result = generate_passage_embeddings_task(passage_ids)
        mock_generate.assert_called_once_with(passage_ids, force=False)
        self.assertEqual(result["processed"], len(passage_ids))


class SemanticSearchAPITests(TestCase):
    def setUp(self):
        self.factory = CoreFactory()
        self.client = APIClient()
        self.user = self.factory.make_user()

    def tearDown(self):
        self.factory.cleanup()

    def test_requires_authentication(self):
        url = reverse("api:semantic-search")
        response = self.client.post(url, {"query": "test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("api.views.build_semantic_answer", return_value={"hits": ["ok"], "answer": {"text": "hello", "citations": []}})
    def test_returns_results(self, mock_search):
        url = reverse("api:semantic-search")
        self.client.force_authenticate(self.user)
        response = self.client.post(url, {"query": "river"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["hits"], ["ok"])
        self.assertIn("answer", data)
        mock_search.assert_called_once()
