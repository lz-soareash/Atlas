"""App core - modelos base reutilizados por todo o Knowledge Core.

Fornece:
  - AtlasModel     : PK UUID, timestamps de criação/atualização, soft delete
  - OwnerMixin     : campo 'owner' (usuário proprietário) - base para ownership/IDOR
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


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
