"""Testes do Cognitive Engine e Integração (Fase 10)."""

import unittest.mock as mock

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import ServiceCredential, User, UserType
from apps.assistant.providers import DeterministicProvider
from apps.audit.models import AuditLog

from .models import CognitiveSession, IntegrationEvent, SessionMessage


def _patch_provider(owner):
    """Força o uso do fallback determinístico nos testes (sem chamada externa)."""
    patcher = mock.patch(
        "apps.cognitive.services.resolve_chat_provider",
        return_value=DeterministicProvider(),
    )
    patcher.start()
    owner.addCleanup(patcher.stop)


def _sessions_url():
    return reverse("cognitive-session-list")


def _session_rotate_url(pk, suffix="query"):
    return reverse(f"cognitive-session-{suffix}", args=[pk])


def _events_url():
    return reverse("integration-event-list")


class CognitiveSessionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cog@atlas.test", password="senha-forte-123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        _patch_provider(self)

    def _create_session(self, **overrides):
        payload = {
            "name": "Projeto Atlas",
            "project_context": {"goal": "estruturar a hipótese"},
            "metadata": {"origin": "test"},
        }
        payload.update(overrides)
        resp = self.client.post(_sessions_url(), payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.data

    def test_create_and_list_session(self):
        data = self._create_session()
        self.assertEqual(data["name"], "Projeto Atlas")
        self.assertTrue(data["is_active"])
        self.assertEqual(data["project_context"]["goal"], "estruturar a hipótese")
        listing = self.client.get(_sessions_url()).data
        self.assertEqual(listing["count"], 1)

    def test_requires_authentication(self):
        anon = APIClient()
        self.assertEqual(
            anon.get(_sessions_url()).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_close_session(self):
        data = self._create_session()
        resp = self.client.post(_session_rotate_url(data["id"], "close"), format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["is_active"])
        self.assertIsNotNone(resp.data["closed_at"])

    def test_query_returns_structured_answer_and_persists_history(self):
        data = self._create_session()
        resp = self.client.post(
            _session_rotate_url(data["id"], "query"),
            {"query": "Resuma o que sei sobre Atlas?"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("answer", resp.data)
        self.assertEqual(resp.data["session_id"], data["id"])
        self.assertIn("sources", resp.data)
        self.assertIn("classification", resp.data)
        self.assertIn("provider", resp.data)
        # histórico persistido (pergunta + resposta)
        self.assertEqual(
            SessionMessage.objects.filter(session_id=data["id"]).count(), 2
        )

    def test_query_requires_non_empty(self):
        data = self._create_session()
        resp = self.client.post(
            _session_rotate_url(data["id"], "query"), {"query": "  "}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_query_on_closed_session_rejected(self):
        data = self._create_session()
        self.client.post(_session_rotate_url(data["id"], "close"), format="json")
        resp = self.client.post(
            _session_rotate_url(data["id"], "query"),
            {"query": "ainda dá?"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anti_idor_other_user_cannot_query_or_close(self):
        other = User.objects.create_user(
            email="outro-cog@atlas.test", password="senha-forte-123"
        )
        session = CognitiveSession.objects.create(owner=other, name="Do outro")
        # outro autenticado não enxerga a sessão → 404
        resp = self.client.post(
            _session_rotate_url(session.pk, "query"), {"query": "oi"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.post(_session_rotate_url(session.pk, "close"), format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_audit_logged_for_session_and_query(self):
        data = self._create_session()
        self.client.post(
            _session_rotate_url(data["id"], "query"), {"query": "oi"}, format="json"
        )
        actions = set(
            AuditLog.objects.filter(user=self.user).values_list("action", flat=True)
        )
        self.assertIn("COGNITIVE_SESSION_CREATE", actions)
        self.assertIn("COGNITIVE_QUERY", actions)

    def test_audit_summary_has_no_secrets(self):
        data = self._create_session()
        log = AuditLog.objects.filter(
            user=self.user, action="COGNITIVE_SESSION_CREATE"
        ).latest("created_at")
        # nunca logar o conteúdo do project_context/payload (só o nome da sessão).
        self.assertNotIn("estruturar a hipótese", log.summary.lower())
        self.assertNotIn("metadata", log.summary.lower())


class IntegrationEventTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="evt@atlas.test", password="senha-forte-123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_accepts_whitelisted_event(self):
        resp = self.client.post(
            _events_url(),
            {"type": "jarvis.notify", "payload": {"note": "olá"}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["type"], "jarvis.notify")
        self.assertTrue(
            AuditLog.objects.filter(user=self.user, action="INTEGRATION_EVENT").exists()
        )

    def test_rejects_unknown_event_type(self):
        resp = self.client.post(
            _events_url(),
            {"type": "jarvis.inject_malicious", "payload": {}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(IntegrationEvent.objects.exists())

    def test_requires_authentication(self):
        anon = APIClient()
        self.assertEqual(
            anon.get(_events_url()).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_antidor_isolated_by_owner(self):
        other = User.objects.create_user(
            email="outro-evt@atlas.test", password="senha-forte-123"
        )
        IntegrationEvent.objects.create(owner=other, type="jarvis.status")
        listing = self.client.get(_events_url()).data
        self.assertEqual(listing["count"], 0)


class CognitiveServiceKeyAuthTests(TestCase):
    """Uma conta de serviço autentica por API key e usa suas próprias sessões."""

    def setUp(self):
        self.svc_user = User.objects.create_user(
            email="svc-cog@atlas.test", password="x"
        )
        self.svc_user.type = UserType.SERVICE
        self.svc_user.save(update_fields=["type"])
        self.raw_key = ServiceCredential.generate_key()
        ServiceCredential.objects.create(
            user=self.svc_user,
            name="Jarvis",
            scopes=["cognitive"],
            key_hash=ServiceCredential._hash(self.raw_key),
            key_hint=ServiceCredential._hint(self.raw_key),
        )
        self.client = APIClient()
        self.client.credentials(HTTP_X_API_KEY=self.raw_key)
        _patch_provider(self)

    def test_service_user_can_open_and_query_session(self):
        create = self.client.post(
            _sessions_url(),
            {"name": "Jarvis", "project_context": {"task": "analisar"}},
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        sid = create.data["id"]
        resp = self.client.post(
            _session_rotate_url(sid, "query"), {"query": "análise"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("answer", resp.data)

    def test_service_user_session_isolated_from_human(self):
        create = self.client.post(
            _sessions_url(), {"name": "Jarvis"}, format="json"
        )
        svc_sid = create.data["id"]
        # humano autenticado (JWT) não enxerga a sessão do serviço
        human = User.objects.create_user(email="human@atlas.test", password="x")
        human_client = APIClient()
        human_client.force_authenticate(user=human)
        self.assertEqual(
            human_client.post(
                _session_rotate_url(svc_sid, "query"), {"query": "oi"}, format="json"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
