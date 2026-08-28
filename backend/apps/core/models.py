"""App core - modelos base reutilizados por todo o Knowledge Core.

Fornece:
  - AtlasModel     : PK UUID, timestamps de criação/atualização, soft delete
  - OwnerMixin     : campo 'owner' (usuário proprietário) - base para ownership/IDOR
  - KnowledgeEntity: modelo abstrato base das entidades do Knowledge Core
                     (title, summary, status) + manager com isolamento por owner
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Status(models.TextChoices):
    """Status padrão das entidades do Knowledge Core."""

    DRAFT = "draft", "Rascunho"
    ACTIVE = "active", "Ativo"
    ARCHIVED = "archived", "Arquivado"
    COMMITTED = "committed", "Convertido"


class AtlasModel(models.Model):
    """Modelo base comum do Atlas.

    - PK: UUID (evita enumeração de IDs -> reforça proteção contra IDOR)
    - created_at / updated_at: timestamps automáticos
    - deleted_at: soft delete (registros marcados, nunca apagados fisicamente)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    # Soft delete
    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])


class OwnerMixin(models.Model):
    """Adiciona o campo 'owner' e garante isolamento por usuário.

    Todas as consultas/escritas devem respeitar o proprietário, evitando IDOR.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_set",
    )

    class Meta:
        abstract = True


class KnowledgeQuerySet(models.QuerySet):
    """QuerySet com filtros de comodidade para as entidades do Knowledge Core."""

    def for_owner(self, user):
        """Somente registros do usuário (isolamento por owner / anti-IDOR)."""
        if user is None or user.is_anonymous:
            return self.none()
        return self.filter(owner=user)

    def active(self):
        """Somente registros não removidos (soft delete)."""
        return self.filter(deleted_at__isnull=True)


class KnowledgeManager(models.Manager.from_queryset(KnowledgeQuerySet)):
    pass


class KnowledgeEntity(AtlasModel, OwnerMixin):
    """Modelo abstrato base das entidades do Knowledge Core.

    Campos compartilhados por Knowledge, Idea, Project, Question, Decision e
    Experience. Cada entidade adiciona seus campos específicos.
    """

    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    objects = KnowledgeManager()

    class Meta:
        abstract = True
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title
