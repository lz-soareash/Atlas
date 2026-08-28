"""Testes do app Experiences."""

from django.test import TestCase

from apps.core.tests_common import EntityCrudTestMixin
from .models import Experience, ExperienceKind


class ExperienceTests(EntityCrudTestMixin, TestCase):
    basename = "experiences"
    model = Experience
    create_payload = {"title": "Erro no migrate", "kind": ExperienceKind.ERROR, "content": "Faltava..."}

    def test_kind_label(self):
        obj = self._create()
        self.assertEqual(obj.data["kind_label"], "Erro")
