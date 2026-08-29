"""Testes da Fase 4 — SEARCH + EMBEDDINGS."""

from unittest import mock

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.decisions.models import Decision
from apps.experiences.models import Experience
from apps.ideas.models import Idea
from apps.knowledge.models import Knowledge
from apps.projects.models import Project
from apps.questions.models import Question

from .embeddings import (
    FingerprintEmbeddingProvider,
    GeminiEmbeddingProvider,
    cosine_similarity,
    resolve_embedding_provider,
)
from .service import SearchService


class SearchEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        self.other = User.objects.create_user(email="b@atlas.test", password="senha-forte-123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse("search")
        # Sem chamadas reais à API: usa o fallback determinístico de embeddings.
        patcher = mock.patch(
            "apps.search.service.resolve_embedding_provider",
            return_value=FingerprintEmbeddingProvider(),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_requires_auth(self):
        resp = APIClient().get(self.url, {"q": "django"})
        self.assertEqual(resp.status_code, 401)

    def test_empty_query_returns_no_results(self):
        resp = self.client.get(self.url, {"q": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["results"], [])

    def test_textual_search_across_entities(self):
        Knowledge.objects.create(owner=self.user, title="Django REST")
        Idea.objects.create(owner=self.user, title="Ideia de Django")
        Project.objects.create(owner=self.user, name="Projeto Atlas")
        resp = self.client.get(self.url, {"q": "django"})
        self.assertEqual(resp.status_code, 200)
        titles = {(r["entity"], r["title"]) for r in resp.data["results"]}
        self.assertIn(("knowledge", "Django REST"), titles)
        self.assertIn(("idea", "Ideia de Django"), titles)
        self.assertNotIn("Projeto Atlas", [r["title"] for r in resp.data["results"]])

    def test_isolated_by_owner(self):
        Knowledge.objects.create(owner=self.other, title="Segredo Django")
        resp = self.client.get(self.url, {"q": "django"})
        self.assertEqual(resp.data["results"], [])

    def test_invalid_type_rejected(self):
        resp = self.client.get(self.url, {"q": "x", "type": "nao-existe"})
        self.assertEqual(resp.status_code, 400)

    def test_type_filter(self):
        Knowledge.objects.create(owner=self.user, title="Django REST")
        Project.objects.create(owner=self.user, name="Projeto Django")
        resp = self.client.get(self.url, {"q": "django", "type": "knowledge"})
        self.assertTrue(resp.data["results"])
        for r in resp.data["results"]:
            self.assertEqual(r["entity"], "knowledge")

    def test_title_ranks_higher_than_body(self):
        k_title = Knowledge.objects.create(owner=self.user, title="PostgreSQL tuning")
        k_body = Knowledge.objects.create(
            owner=self.user, title="Banco", content="discussão sobre tuning de postgresql"
        )
        items = SearchService().search(self.user, "tuning")
        ranked = [i["id"] for i in items["results"]]
        self.assertLess(ranked.index(str(k_title.pk)), ranked.index(str(k_body.pk)))

    def test_excludes_soft_deleted(self):
        k = Knowledge.objects.create(owner=self.user, title="Django REST")
        k.soft_delete()
        resp = self.client.get(self.url, {"q": "django"})
        self.assertEqual(resp.data["results"], [])

    def test_result_shape(self):
        Knowledge.objects.create(owner=self.user, title="Django REST")
        resp = self.client.get(self.url, {"q": "django"})
        item = resp.data["results"][0]
        for field in ["id", "entity", "label", "title", "snippet", "score", "route", "status", "source"]:
            self.assertIn(field, item)

    def test_semantic_run_with_fallback(self):
        Knowledge.objects.create(owner=self.user, title="Django REST framework")
        resp = self.client.get(self.url, {"q": "django"})
        self.assertTrue(resp.data["semantic_available"])


class EmbeddingProvidersTests(TestCase):
    def test_fingerprint_is_available_and_deterministic(self):
        p = FingerprintEmbeddingProvider()
        self.assertTrue(p.available())
        a = p.embed_documents(["django rest"])
        b = p.embed_documents(["django rest"])
        self.assertEqual(a, b)
        self.assertEqual(len(a[0]), FingerprintEmbeddingProvider.dim)

    def test_cosine_similarity_between_related_texts(self):
        p = FingerprintEmbeddingProvider()
        [v1] = p.embed_documents(["Django REST framework"])
        [v2] = p.embed_documents(["django rest framework api"])
        [v3] = p.embed_documents(["picadinho de batata"])
        s_related = cosine_similarity(v1, v2)
        s_unrelated = cosine_similarity(v1, v3)
        self.assertGreater(s_related, s_unrelated)

    def test_resolve_returns_fallback_without_key(self):
        with mock.patch("apps.search.embeddings.GeminiEmbeddingProvider.available", return_value=False):
            provider = resolve_embedding_provider()
            self.assertIsInstance(provider, FingerprintEmbeddingProvider)

    def test_resolve_returns_gemini_with_key(self):
        with mock.patch("apps.search.embeddings.GeminiEmbeddingProvider.available", return_value=True), \
             mock.patch(
                 "apps.search.embeddings.GeminiEmbeddingProvider.embed_documents",
                 return_value=[[0.1, 0.2, 0.3]],
             ):
            provider = resolve_embedding_provider()
            self.assertIsInstance(provider, GeminiEmbeddingProvider)
            self.assertEqual(provider.embed_documents(["x"]), [[0.1, 0.2, 0.3]])

    @mock.patch("apps.search.embeddings.GeminiEmbeddingProvider.available", return_value=True)
    def test_gemini_embeds_via_sdk(self, _avail):
        client = mock.MagicMock()
        result = mock.MagicMock()
        result.embeddings = [mock.Mock(values=[0.5, 0.5, 0.5])]
        client.models.embed_content.return_value = result
        with mock.patch("google.genai.Client", return_value=client):
            p = GeminiEmbeddingProvider(api_key="fake-key")
            self.assertEqual(p.embed_documents(["olá"]), [[0.5, 0.5, 0.5]])
            client.models.embed_content.assert_called_once()

    def test_gemini_raises_without_key(self):
        with mock.patch("apps.search.embeddings.settings.GEMINI_API_KEY", ""):
            p = GeminiEmbeddingProvider(api_key=None)
            self.assertFalse(p.available())
