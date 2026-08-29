"""Modelos do app Intelligence (Fase 8).

- InboxItem: captura rápida de pensamentos soltos; a IA sugere o tipo e o
  destino, mas NADA é movido automaticamente (o usuário decide).
"""

from django.db import models

from apps.core.models import AtlasModel, KnowledgeManager, OwnerMixin


class InboxStatus(models.TextChoices):
    OPEN = "open", "Aberto"
    CLASSIFIED = "classified", "Classificado"
    ARCHIVED = "archived", "Arquivado"


class InboxItem(AtlasModel, OwnerMixin):
    """Item solto do Inbox, aguardando classificação/destino pelo usuário."""

    content = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=InboxStatus.choices,
        default=InboxStatus.OPEN,
    )
    # Classificação sugerida pela IA (não é aplicada sem confirmação).
    kind = models.CharField(max_length=40, blank=True)
    destination = models.CharField(max_length=80, blank=True)
    summary = models.TextField(blank=True)

    objects = KnowledgeManager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Item do Inbox"
        verbose_name_plural = "Itens do Inbox"

    def __str__(self):
        return self.content[:60]
