"""Entidade Knowledge — conhecimento adquirido.

Ex.: Django, PostgreSQL, REST, JWT, Docker, Redis.
"""

from django.db import models

from apps.core.models import KnowledgeEntity


class DomainLevel(models.IntegerChoices):
    BEGINNER = 1, "Iniciante"
    INTERMEDIATE = 2, "Intermediário"
    ADVANCED = 3, "Avançado"
    EXPERT = 4, "Especialista"


class Knowledge(KnowledgeEntity):
    content = models.TextField(blank=True)
    domain_level = models.PositiveSmallIntegerField(
        choices=DomainLevel.choices,
        default=DomainLevel.BEGINNER,
    )
    tags = models.JSONField(default=list, blank=True)

    class Meta(KnowledgeEntity.Meta):
        verbose_name = "Conhecimento"
        verbose_name_plural = "Conhecimentos"

    @property
    def domain_level_label(self):
        return DomainLevel(self.domain_level).label if self.domain_level in DomainLevel.values else ""
