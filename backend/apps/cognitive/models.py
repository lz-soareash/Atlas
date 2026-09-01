"""Modelos do Cognitive Engine (Fase 10).

Sessões cognitivas persistentes (com histórico) e eventos de integração.
Todos os modelos seguem os padrões anti-IDOR do Atlas (OwnerMixin +
AtlasModel) e o soft delete padrão.
"""

from django.db import models
from django.utils import timezone

from apps.core.models import AtlasModel, KnowledgeManager, OwnerMixin


class CognitiveSession(AtlasModel, OwnerMixin):
    """Sessão cognitiva persistida por owner.

    Dá estabilidade à integração: um cliente (ex.: Jarvis) abre uma sessão,
    informa um `project_context` (contexto do projeto em andamento) e recebe
    respostas estruturadas e contextuais, com histórico persistido.
    """

    name = models.CharField(max_length=120, blank=True)
    project_context = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Sessão cognitiva"
        verbose_name_plural = "Sessões cognitivas"
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["owner", "is_active"])]

    def __str__(self):
        return f"{self.name or 'Sessão'} ({self.pk})"

    def close(self):
        self.is_active = False
        self.closed_at = timezone.now()
        self.save(update_fields=["is_active", "closed_at", "updated_at"])

    objects = KnowledgeManager()


class SessionMessage(AtlasModel, OwnerMixin):
    """Mensagem de uma sessão cognitiva (histórico persistido do turno)."""

    session = models.ForeignKey(
        CognitiveSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20)  # user | assistant
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)

    objects = KnowledgeManager()

    class Meta:
        verbose_name = "Mensagem de sessão"
        verbose_name_plural = "Mensagens de sessão"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"


class IntegrationEvent(AtlasModel, OwnerMixin):
    """Evento de integração aceito pelo Atlas (whitelist extensível).

    Um cliente externo (ex.: Jarvis) publica eventos aqui. O tipo segue a
    whitelist em `apps.cognitive.integration.INTEGRATION_EVENT_TYPES`, que pode
    ser estendida sem quebrar contratos existentes.
    """

    type = models.CharField(max_length=50)
    payload = models.JSONField(default=dict, blank=True)
    processed = models.BooleanField(default=False)
    error = models.CharField(max_length=500, blank=True)

    objects = KnowledgeManager()

    class Meta:
        verbose_name = "Evento de integração"
        verbose_name_plural = "Eventos de integração"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "type"])]

    def __str__(self):
        return f"{self.type} ({'ok' if self.processed else 'pendente'})"
