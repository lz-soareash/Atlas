"""Entidade Experience — experiências.

Tipos: erro encontrado, solução, descoberta, experimento, aprendizado.
"""

from django.db import models

from apps.core.models import KnowledgeEntity


class ExperienceKind(models.TextChoices):
    ERROR = "error", "Erro"
    SOLUTION = "solution", "Solução"
    DISCOVERY = "discovery", "Descoberta"
    EXPERIMENT = "experiment", "Experimento"
    LESSON = "lesson", "Aprendizado"


class Experience(KnowledgeEntity):
    kind = models.CharField(
        max_length=20,
        choices=ExperienceKind.choices,
        default=ExperienceKind.LESSON,
    )
    content = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    class Meta(KnowledgeEntity.Meta):
        verbose_name = "Experiência"
        verbose_name_plural = "Experiências"

    @property
    def kind_label(self):
        return ExperienceKind(self.kind).label if self.kind else ""
