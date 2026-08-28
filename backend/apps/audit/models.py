"""Auditoria do Atlas.

Registra ações relevantes do sistema (auth, CRUD, IA) de forma imutável e
rastreável. NUNCA registra secrets (API keys, senhas, tokens).
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=120, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)
    summary = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.entity_type}"

    @classmethod
    def _safe(cls, data):
        """Remove campos sensíveis antes de gravar (defesa em profundidade)."""
        forbidden = {"password", "token", "secret", "api_key", "authorization"}
        if not isinstance(data, dict):
            return data
        safe = {}
        for key, value in data.items():
            if any(word in key.lower() for word in forbidden):
                safe[key] = "[REDACTED]"
            elif isinstance(value, dict):
                safe[key] = cls._safe(value)
            else:
                safe[key] = value
        return safe

    @classmethod
    def log(
        cls,
        user=None,
        action="ACTION",
        entity_type="",
        entity_id="",
        summary="",
        details=None,
        ip_address=None,
    ):
        """Cria um registro de auditoria com sanitização de secrets."""
        return cls.objects.create(
            user=user,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else "",
            summary=summary,
            details=cls._safe(details or {}),
            ip_address=ip_address,
        )
