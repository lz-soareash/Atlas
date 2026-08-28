"""Testes do app Ideas (inclui transformação para Projeto)."""

from django.test import TestCase
from django.urls import reverse

from apps.core.models import Status
from apps.core.tests_common import EntityCrudTestMixin
from apps.projects.models import Project
from .models import Idea


class IdeaTests(EntityCrudTestMixin, TestCase):
    basename = "ideas"
    model = Idea
    create_payload = {"title": "Granja", "description": "Automatizar granja"}

    def test_convert_creates_project(self):
        idea = self._create().data
        url = reverse("ideas-convert", args=[idea["id"]])
        resp = self.client.post(url, {"name": "Projeto Granja"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Project.objects.filter(owner=self.user).count(), 1)
        refreshed = Idea.objects.get(pk=idea["id"])
        self.assertTrue(refreshed.converted)
        self.assertEqual(refreshed.status, Status.COMMITTED)
        self.assertEqual(str(refreshed.project_id), resp.data["id"])

    def test_convert_other_returns_404(self):
        other_idea = self._make_obj_for(self.other)
        url = reverse("ideas-convert", args=[other_idea.pk])
        resp = self.client.post(url, {"name": "X"}, format="json")
        self.assertEqual(resp.status_code, 404)
