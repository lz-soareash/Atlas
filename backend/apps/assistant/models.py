"""Modelos do Atlas Assistant (Fase 6).

Memória persistente do usuário: preferências, contexto, objetivos e registros
relevantes. Nada é salvo automaticamente — memórias são criadas explicitamente
pelo usuário (ou, futuramente, sugeridas e confirmadas pelo Assistente).
"""

from django.db import models

from apps.core.models import AtlasModel, KnowledgeManager, OwnerMixin


class MemoryKind(models.TextChoices):
    PREFERENCE = "preferencia", "Preferência"
    CONTEXT = "contexto", "Contexto"
    GOAL = "objetivo", "Objetivo"
    PROJECT = "projeto", "Projeto"
    DECISION = "decisao", "Decisão"
    EXPERIENCE = "experiencia", "Experiência"


class Memory(AtlasModel, OwnerMixin):
    """Uma memória explícita do usuário, usada como contexto pelo chat."""

    kind = models.CharField(
        max_length=20,
        choices=MemoryKind.choices,
        default=MemoryKind.CONTEXT,
    )
    content = models.TextField()

    objects = KnowledgeManager()

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Memória"
        verbose_name_plural = "Memórias"
        indexes = [models.Index(fields=["owner", "kind"])]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.content[:60]}"

    @property
    def kind_label(self):
        return self.get_kind_display()