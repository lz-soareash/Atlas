"""Entidade Decision — uma decisão tomada.

Estrutura: contexto, problema, alternativas, decisão, justificativa,
consequências e data.
"""

from django.db import models

from apps.core.models import KnowledgeEntity


class Decision(KnowledgeEntity):
    context = models.TextField(blank=True)
    problem = models.TextField(blank=True)
    alternatives = models.JSONField(default=list, blank=True)
    decision = models.TextField(blank=True)
    rationale = models.TextField(blank=True)
    consequences = models.TextField(blank=True)
    decided_at = models.DateField(null=True, blank=True)

    class Meta(KnowledgeEntity.Meta):
        verbose_name = "Decisão"
        verbose_name_plural = "Decisões"
