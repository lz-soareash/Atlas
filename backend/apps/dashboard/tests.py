"""Testes do endpoint de Dashboard (contagens + recentes)."""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.knowledge.models import Knowledge
from apps.ideas.models import Idea
from apps.projects.models import Project


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        self.other = User.objects.create_user(email="b@atlas.test", password="senha-forte-123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse("dashboard")

    def test_all_counts_included(self):
        Knowledge.objects.create(owner=self.user, title="Django")
        Idea.objects.create(owner=self.user, title="Idéia")
        Project.objects.create(owner=self.user, name="Projeto")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        keys = [c["key"] for c in resp.data["counts"]]
        for expected in ["conhecimentos", "ideias", "projetos", "perguntas", "decisoes", "experiencias"]:
            self.assertIn(expected, keys)
        counts_by_key = {c["key"]: c["count"] for c in resp.data["counts"]}
        self.assertEqual(counts_by_key["conhecimentos"], 1)
        self.assertEqual(counts_by_key["projetos"], 1)
        self.assertEqual(resp.data["total"], 3)

    def test_isolated_by_owner(self):
        Knowledge.objects.create(owner=self.other, title="Privado")
        resp = self.client.get(self.url)
        counts_by_key = {c["key"]: c["count"] for c in resp.data["counts"]}
        self.assertEqual(counts_by_key["conhecimentos"], 0)

    def test_recent_contains_items(self):
        Knowledge.objects.create(owner=self.user, title="Django")
        resp = self.client.get(self.url)
        titles = [r["title"] for r in resp.data["recent"]]
        self.assertIn("Django", titles)

    def test_excludes_soft_deleted(self):
        k = Knowledge.objects.create(owner=self.user, title="Django")
        k.soft_delete()
        resp = self.client.get(self.url)
        counts_by_key = {c["key"]: c["count"] for c in resp.data["counts"]}
        self.assertEqual(counts_by_key["conhecimentos"], 0)

    def test_requires_auth(self):
        anon = APIClient()
        resp = anon.get(self.url)
        self.assertEqual(resp.status_code, 401)
