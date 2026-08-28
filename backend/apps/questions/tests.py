"""Testes do app Questions (inclui transformação para Conhecimento)."""

from django.test import TestCase
from django.urls import reverse

from apps.core.models import Status
from apps.core.tests_common import EntityCrudTestMixin
from apps.knowledge.models import Knowledge
from .models import Question


class QuestionTests(EntityCrudTestMixin, TestCase):
    basename = "questions"
    model = Question
    create_payload = {"title": "Como funciona Gemini?", "question_text": "Explicar"}

    def test_respond_creates_knowledge(self):
        q = self._create().data
        url = reverse("questions-respond", args=[q["id"]])
        resp = self.client.post(url, {"content": "IA generativa"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Knowledge.objects.filter(owner=self.user).count(), 1)
        refreshed = Question.objects.get(pk=q["id"])
        self.assertTrue(refreshed.answered)
        self.assertEqual(refreshed.status, Status.COMMITTED)
        self.assertEqual(str(refreshed.knowledge_id), resp.data["id"])

    def test_respond_other_returns_404(self):
        other_q = self._make_obj_for(self.other)
        url = reverse("questions-respond", args=[other_q.pk])
        resp = self.client.post(url, {"content": "X"}, format="json")
        self.assertEqual(resp.status_code, 404)
