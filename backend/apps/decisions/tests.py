"""Testes do app Decisions."""

from django.test import TestCase

from apps.core.tests_common import EntityCrudTestMixin
from .models import Decision


class DecisionTests(EntityCrudTestMixin, TestCase):
    basename = "decisions"
    model = Decision
    create_payload = {
        "title": "Stack back-end",
        "context": "Definir linguagem",
        "problem": "Qual tecnologia?",
        "alternatives": ["Python", "Node"],
        "decision": "Python/Django",
        "rationale": "Produtividade",
    }
