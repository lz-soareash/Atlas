"""Testes do app Knowledge."""

from django.test import TestCase
from django.urls import reverse

from apps.core.models import Status
from apps.core.tests_common import EntityCrudTestMixin
from .models import Knowledge


class KnowledgeTests(EntityCrudTestMixin, TestCase):
    basename = "knowledge"
    model = Knowledge
    create_payload = {"title": "Django", "content": "Framework web"}

    def test_search(self):
        self.client.post(self.list_url(), {"title": "PostgreSQL"}, format="json")
        resp = self.client.get(self.list_url(), {"search": "Postgre"})
        self.assertEqual(resp.data["count"], 1)

    def test_status_choices(self):
        resp = self._create(status=Status.ACTIVE)
        self.assertEqual(resp.data["status"], "active")
