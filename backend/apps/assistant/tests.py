"""Testes da Fase 5 — GEMINI CORE.

Cobrem o GeminiProvider (SDK mockado), o fallback determinístico, o serviço de
chat (com isolamento por owner e fontes rastreáveis) e o endpoint HTTP. Nenhum
teste faz chamada real à API (sempre mockado ou determinístico).
"""

from unittest import mock

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.knowledge.models import Knowledge
from apps.projects.models import Project
from apps.search.embeddings import FingerprintEmbeddingProvider

from .exceptions import (
    AIError,
    MaxRetriesExceededError,
    ProviderUnavailableError,
    RateLimitExceededError,
    TokenLimitError,
)
from .models import Memory
from .providers import DeterministicProvider, GeminiProvider, resolve_chat_provider
from .retry import retry_with_backoff
from .services import ChatService
from .services.chat import parse_classification


def _givenai():
    """Provider determinístico com registro de chamadas (para asserts)."""
    return DeterministicProvider()


class StubProvider(DeterministicProvider):
    """Provider que devolve um texto fixo (para testar classificação)."""

    def __init__(self, answer: str):
        self.answer = answer

    def generate_text(self, messages, *args, **kwargs):
        return {"content": self.answer, "tool_calls": []}


def _patch_embeddings(testcase):
    """Evita chamadas reais à API nos testes: usa o fallback de embeddings."""
    patcher = mock.patch(
        "apps.search.service.resolve_embedding_provider",
        return_value=FingerprintEmbeddingProvider(),
    )
    patcher.start()
    testcase.addCleanup(patcher.stop)


# ---------------- GeminiProvider ----------------

class GeminiProviderTests(TestCase):
    def setUp(self):
        self.p = GeminiProvider(api_key="fake-key", model="x")

    def _sdk(self, text="olá"):
        client = mock.MagicMock()
        resp = mock.MagicMock()
        resp.text = text
        resp.candidates = []
        client.models.generate_content.return_value = resp
        return client

    @mock.patch("apps.assistant.providers.gemini.GeminiProvider.available", return_value=True)
    def test_generate_text_returns_content(self, _):
        client = self._sdk("resposta legal")
        with mock.patch("apps.assistant.providers.gemini.Client", return_value=client):
            out = self.p.generate_text([{"role": "user", "content": "oi"}])
        self.assertEqual(out["content"], "resposta legal")
        self.assertEqual(out["tool_calls"], [])

    @mock.patch("apps.assistant.providers.gemini.GeminiProvider.available", return_value=True)
    def test_includes_system_and_config(self, _):
        client = self._sdk()
        with mock.patch("apps.assistant.providers.gemini.Client", return_value=client):
            self.p.generate_text(
                [{"role": "system", "content": "Seja breve"}, {"role": "user", "content": "oi"}],
                temperature=0.2,
                max_tokens=512,
            )
        call = client.models.generate_content.call_args.kwargs
        self.assertIn("config", call)
        cfg = call["config"]
        self.assertEqual(cfg.temperature, 0.2)
        self.assertEqual(cfg.max_output_tokens, 512)
        self.assertIn("Seja breve", cfg.system_instruction)

    @mock.patch("apps.assistant.providers.gemini.GeminiProvider.available", return_value=True)
    def test_retries_on_transient_error(self, _):
        client = mock.MagicMock()
        resp = mock.MagicMock()
        resp.text = "ok após retry"
        resp.candidates = []
        client.models.generate_content.side_effect = [
            Exception("429 Too Many Requests"),
            resp,
        ]
        with mock.patch("apps.assistant.providers.gemini.Client", return_value=client), \
             mock.patch("time.sleep", return_value=None):
            out = self.p.generate_text([{"role": "user", "content": "oi"}])
        self.assertEqual(client.models.generate_content.call_count, 2)
        self.assertEqual(out["content"], "ok após retry")

    @mock.patch("apps.assistant.providers.gemini.GeminiProvider.available", return_value=True)
    def test_quota_mapped_to_rate_limit(self, _):
        client = mock.MagicMock()
        client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")
        with mock.patch("apps.assistant.providers.gemini.Client", return_value=client), \
             mock.patch("time.sleep", return_value=None):
            with self.assertRaises(RateLimitExceededError):
                self.p.generate_text([{"role": "user", "content": "oi"}])

    def test_unavailable_without_key(self):
        with mock.patch("apps.assistant.providers.gemini.settings.GEMINI_API_KEY", ""):
            p = GeminiProvider(api_key=None, model="x")
            self.assertFalse(p.available())
            with self.assertRaises(ProviderUnavailableError):
                p.generate_text([{"role": "user", "content": "oi"}])

    @mock.patch("apps.assistant.providers.gemini.GeminiProvider.available", return_value=True)
    def test_extracts_tool_calls(self, _):
        from google.genai import types

        part = mock.MagicMock(spec=types.Part)
        fn = mock.MagicMock()
        fn.name = "get_entity"
        fn.args = {"id": "abc"}
        part.function_call = fn
        resp = mock.MagicMock()
        resp.text = ""
        resp.candidates = [mock.MagicMock(content=mock.MagicMock(parts=[part]))]
        client = mock.MagicMock()
        client.models.generate_content.return_value = resp
        with mock.patch("apps.assistant.providers.gemini.Client", return_value=client):
            out = self.p.generate_text([{"role": "user", "content": "bach"}])
        self.assertEqual(out["tool_calls"], [{"name": "get_entity", "args": {"id": "abc"}}])


# ---------------- DeterministicProvider / resolve ----------------

class DeterministicProviderTests(TestCase):
    def test_always_available(self):
        self.assertTrue(DeterministicProvider().available())

    def test_answers_with_sources(self):
        ctx = {
            "sources": [{"entity": "knowledge", "title": "Django", "snippet": "..."}],
            "graph_edges": [],
        }
        out = DeterministicProvider().generate_text(
            [{"role": "user", "content": "o que sei sobre django?"}], context=ctx
        )
        self.assertIn("Django", out["content"])
        self.assertIn("🧠", out["content"])

    def test_answer_without_sources(self):
        out = DeterministicProvider().generate_text(
            [{"role": "user", "content": "tudo"}], context={"sources": [], "graph_edges": []}
        )
        self.assertIn("Nenhuma fonte", out["content"])

    def test_resolve_uses_gemini_when_available(self):
        with mock.patch("apps.assistant.providers.GeminiProvider.available", return_value=True):
            self.assertIsInstance(resolve_chat_provider(), GeminiProvider)


class RetryTests(TestCase):
    def test_returns_after_retry(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] < 2:
                raise Exception("503 Service Unavailable")
            return "done"

        with mock.patch("time.sleep", return_value=None):
            self.assertEqual(retry_with_backoff(fn, max_retries=3), "done")
        self.assertEqual(calls["n"], 2)

    def test_propagates_non_transient(self):
        with mock.patch("time.sleep", return_value=None):
            with self.assertRaises(ValueError):
                retry_with_backoff(lambda: (_ for _ in ()).throw(ValueError("boom")), max_retries=2)

    def test_retries_on_timeout(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] < 2:
                raise ConnectionError("The handshake operation timed out")
            return "ok"

        with mock.patch("time.sleep", return_value=None):
            self.assertEqual(retry_with_backoff(fn, max_retries=3), "ok")
        self.assertEqual(calls["n"], 2)


# ---------------- ChatService ----------------

class ChatServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        self.other = User.objects.create_user(email="b@atlas.test", password="senha-forte-123")
        Knowledge.objects.create(owner=self.user, title="Django REST")
        Project.objects.create(owner=self.other, name="Segredo alheio")
        _patch_embeddings(self)

    def test_returns_answer_and_sources_isolated(self):
        svc = ChatService(provider=DeterministicProvider())
        data = svc.chat(self.user, [{"role": "user", "content": "django"}])
        self.assertEqual(data["provider"], "deterministic")
        titles = [s["title"] for s in data["sources"]]
        self.assertIn("Django REST", titles)
        self.assertNotIn("Segredo alheio", [s["title"] for s in data["sources"]])
        self.assertEqual(data["classification"]["kind"], "fato")

    def test_classification_suggestion_without_sources(self):
        svc = ChatService(provider=DeterministicProvider())
        data = svc.chat(self.user, [{"role": "user", "content": "zzzz não existe"}])
        self.assertEqual(data["classification"]["kind"], "sugestao")
        self.assertEqual(data["sources"], [])

    def test_empty_messages_rejected(self):
        svc = ChatService(provider=DeterministicProvider())
        with self.assertRaises(AIError):
            svc.chat(self.user, [])

    def test_limits_history_size(self):
        svc = ChatService(provider=DeterministicProvider())
        many = [{"role": "user", "content": f"mensagem {i}"} for i in range(100)]
        data = svc.chat(self.user, many)
        self.assertIsInstance(data["answer"], str)
        self.assertTrue(data["answer"])

    def test_passes_context_to_provider(self):
        captured = {}

        class Capturing(DeterministicProvider):
            def generate_text(self, messages, **kwargs):
                captured["context"] = kwargs.get("context")
                captured["messages"] = messages
                return super().generate_text(messages, **kwargs)

        ChatService(provider=Capturing()).chat(self.user, [{"role": "user", "content": "django"}])
        self.assertIn("context", captured)
        self.assertIn("sources", captured["context"])
        titles = [s["title"] for s in captured["context"]["sources"]]
        self.assertIn("Django REST", titles)


# ---------------- Classificação (Fase 6) ----------------

class ClassificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        _patch_embeddings(self)

    def test_parses_all_tags(self):
        cases = [
            ("[FATO] Django é X", "Django é X", "fato"),
            ("[INFERÊNCIA] Logo Y", "Logo Y", "inferencia"),
            ("[SUGESTÃO] Tente Z", "Tente Z", "sugestao"),
            ("[INFORMAÇÃO EXTERNA] Sobre k8s", "Sobre k8s", "informacao_externa"),
        ]
        for raw, expect_rest, expect_kind in cases:
            rest, cls = parse_classification(raw, has_sources=False)
            self.assertEqual(rest, expect_rest)
            self.assertEqual(cls["kind"], expect_kind)

    def test_strips_tag_without_leading_space(self):
        rest, cls = parse_classification("[FATO]Conteúdo", has_sources=False)
        self.assertEqual(rest, "Conteúdo")
        self.assertEqual(cls["kind"], "fato")

    def test_fallback_to_fact_with_sources(self):
        rest, cls = parse_classification("Texto sem tag", has_sources=True)
        self.assertEqual(rest, "Texto sem tag")
        self.assertEqual(cls["kind"], "fato")
        self.assertTrue(cls["source_based"])

    def test_fallback_to_suggestion_without_sources(self):
        _, cls = parse_classification("Texto sem tag", has_sources=False)
        self.assertEqual(cls["kind"], "sugestao")

    def test_chat_with_stub_provider_classifies(self):
        svc = ChatService(provider=StubProvider("[INFERÊNCIA] Provavelmente vocês usam Django."))
        data = svc.chat(self.user, [{"role": "user", "content": "o que acham?"}])
        self.assertEqual(data["classification"]["kind"], "inferencia")
        self.assertTrue(data["answer"].startswith("Provavelmente"))


# ---------------- Memória (Fase 6) ----------------

class MemoryContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        self.other = User.objects.create_user(email="b@atlas.test", password="senha-forte-123")
        _patch_embeddings(self)

    def test_memories_injected_into_context(self):
        Memory.objects.create(owner=self.user, kind="objetivo", content="Quero dominar Django")
        Memory.objects.create(owner=self.other, kind="preferencia", content="Segredo alheio")
        captured = {}

        class Capturing(DeterministicProvider):
            def generate_text(self, messages, **kwargs):
                captured["context"] = kwargs.get("context")
                return super().generate_text(messages, **kwargs)

        ChatService(provider=Capturing()).chat(self.user, [{"role": "user", "content": "oi"}])
        memories = captured["context"]["memories"]
        self.assertEqual(len(memories), 1)
        self.assertIn("Quero dominar Django", memories[0]["content"])
        self.assertNotIn("Segredo alheio", [m["content"] for m in memories])

    def test_deterministic_answer_uses_memories(self):
        Memory.objects.create(owner=self.user, kind="preferencia", content="Prefiro respostas curtas")
        svc = ChatService(provider=DeterministicProvider())
        data = svc.chat(self.user, [{"role": "user", "content": "zzz inexistente"}])
        self.assertIn("Prefiro respostas curtas", data["answer"])
        self.assertEqual(data["classification"]["kind"], "sugestao")


# ---------------- Memória Endpoint (Fase 6) ----------------

class MemoryEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        self.other = User.objects.create_user(email="b@atlas.test", password="senha-forte-123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.list_url = reverse("memories-list")

    def test_create_and_list(self):
        resp = self.client.post(
            self.list_url,
            {"kind": "objetivo", "content": "Aprender Flask"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["kind_label"], "Objetivo")
        lst = self.client.get(self.list_url)
        self.assertEqual(len(lst.data["results"]), 1)

    def test_isolated_by_owner(self):
        Memory.objects.create(owner=self.other, kind="contexto", content="Alheio")
        lst = self.client.get(self.list_url)
        self.assertEqual(len(lst.data["results"]), 0)

    def test_delete_is_soft(self):
        m = Memory.objects.create(owner=self.user, kind="contexto", content="x")
        del_resp = self.client.delete(f"{self.list_url}{m.pk}/")
        self.assertEqual(del_resp.status_code, 204)
        lst = self.client.get(self.list_url)
        self.assertEqual(len(lst.data["results"]), 0)
        self.assertTrue(Memory.objects.filter(pk=m.pk).exists())


# ---------------- Endpoint ----------------

class ChatEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse("assistant-chat")
        Knowledge.objects.create(owner=self.user, title="Django REST")
        _patch_embeddings(self)

    def test_requires_auth(self):
        resp = APIClient().post(self.url, {"messages": [{"role": "user", "content": "oi"}]}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_missing_messages_400(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    @mock.patch("apps.assistant.services.chat.resolve_chat_provider", return_value=DeterministicProvider())
    def test_returns_chat_payload(self, _r):
        resp = self.client.post(
            self.url,
            {"messages": [{"role": "user", "content": "django"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        for field in ["answer", "sources", "provider", "classification", "semantic_available"]:
            self.assertIn(field, resp.data)

    @mock.patch("apps.assistant.services.chat.resolve_chat_provider", return_value=DeterministicProvider())
    def test_rate_limited_returns_429(self, _r):
        from apps.assistant.throttling import GeminiRateThrottle

        with mock.patch.object(GeminiRateThrottle, "allow_request", return_value=False), \
             mock.patch.object(GeminiRateThrottle, "wait", return_value=30):
            resp = self.client.post(
                self.url,
                {"messages": [{"role": "user", "content": "django"}]},
                format="json",
            )
        self.assertEqual(resp.status_code, 429)
