"""Testes do app Projects."""

from django.test import TestCase

from apps.core.tests_common import EntityCrudTestMixin
from .models import Project


class ProjectTests(EntityCrudTestMixin, TestCase):
    basename = "projects"
    model = Project
    create_payload = {
        "name": "Atlas",
        "description": "Knowledge Operating System",
        "objective": "Organizar conhecimento",
        "technologies": ["Django", "PostgreSQL", "Gemini"],
    }

    def test_title_synced_to_name(self):
        obj = self._create()
        self.assertEqual(obj.data["title"], "Atlas")
