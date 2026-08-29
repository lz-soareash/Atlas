from unittest import mock

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.knowledge.models import Knowledge
from apps.decisions.models import Decision
from apps.experiences.models import Experience
from apps.ideas.models import Idea
from apps.projects.models import Project
from apps.questions.models import Question
from apps.search.embeddings import FingerprintEmbeddingProvider

from .models import InboxItem, InboxStatus


def _patch_embeddings(testcase):
    patcher = mock.patch(
        "apps.intelligence.services.resolve_embedding_provider",
        return_value=FingerprintEmbeddingProvider(),
    )
    patcher.start()
    testcase.addCleanup(patcher.stop)


class InboxTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse("inbox-list")

    def test_create_and_list(self):
        resp = self.client.post(self.url, {"content": "Pensamento solto"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(self.client.get(self.url).data["results"]), 1)

    def test_classify_suggests_kind_without_moving(self):
        item = InboxItem.objects.create(owner=self.user, content="Tive uma ideia: app de receitas")
        resp = self.client.post(f"{self.url}{item.pk}/classify/")
        self.assertEqual(resp.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.kind, "Ideia")
        self.assertEqual(item.status, InboxStatus.CLASSIFIED)
        # Nada foi criado em outra entidade.
        self.assertFalse(Idea.objects.filter(owner=self.user).exists())

    def test_isolated_by_owner(self):
        from apps.accounts.models import User as U
        other = U.objects.create_user(email="b@atlas.test", password="senha-forte-123")
        InboxItem.objects.create(owner=other, content="secreto")
        self.assertEqual(len(self.client.get(self.url).data["results"]), 0)


class IntelligenceEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        _patch_embeddings(self)

    def test_requires_auth_duplicates(self):
        resp = APIClient().get(reverse("intelligence-duplicates"))
        self.assertEqual(resp.status_code, 401)

    def test_duplicates_detects_similar_titles(self):
        Knowledge.objects.create(owner=self.user, title="Django REST Framework", content="APIs REST em Django")
        Knowledge.objects.create(owner=self.user, title="Django Rest Framework basico", content="APIs com Django REST")
        resp = self.client.get(reverse("intelligence-duplicates"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["groups"]), 1)

    def test_relationship_suggestions(self):
        Knowledge.objects.create(owner=self.user, title="PostgreSQL", content="banco de dados relacional")
        Project.objects.create(owner=self.user, name="App Atlas", description="usa postgresql como banco de dados")
        resp = self.client.get(reverse("intelligence-rel-suggestions"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["suggestions"]), 1)

    def test_gap_analysis(self):
        Question.objects.create(owner=self.user, title="Como funciona kubernetes?", question_text="quero entender kubernetes orquestracao")
        Idea.objects.create(owner=self.user, title="Estudar kubernetes", description="kubernetes e containers")
        # Nenhum Knowledge sobre kubernetes → deve aparecer como gap.
        Knowledge.objects.create(owner=self.user, title="Django", content="framework web")
        resp = self.client.get(reverse("intelligence-gaps"))
        self.assertEqual(resp.status_code, 200)
        words = [g["topic"] for g in resp.data["gaps"]]
        self.assertIn("kubernetes", words)

    def test_productivity_insights_open_questions(self):
        Question.objects.create(owner=self.user, title="Como funciona asyncio?", question_text="")
        resp = self.client.get(reverse("intelligence-insights"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data["summary"]["open_questions"], 1)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_productivity_insights_open_ideas(self):
        Idea.objects.create(owner=self.user, title="App de receitas", description="")
        resp = self.client.get(reverse("intelligence-insights"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data["summary"]["open_ideas"], 1)

    def test_productivity_insights_errors(self):
        Experience.objects.create(owner=self.user, title="erro x", kind="error", content="")
        resp = self.client.get(reverse("intelligence-insights"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data["summary"]["errors_without_solution"], 1)
