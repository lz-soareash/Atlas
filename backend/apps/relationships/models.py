"""Entidade Relationship — relacionamentos genéricos entre entidades do Atlas.

Usa GenericForeignKey para `origin` e `target`, permitindo conectar qualquer
combinação de entidades do Knowledge Core (Knowledge, Idea, Project, Question,
Decision, Experience). Garante isolamento por owner (anti-IDOR).
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

from apps.core.models import AtlasModel, KnowledgeQuerySet, OwnerMixin


class RelationshipType(models.TextChoices):
    """Tipos de relacionamento (configurável e extensível)."""

    RELATED_TO = "RELACIONADO_A", "Relacionado a"
    USES = "USA", "Usa"
    DEPENDS_ON = "DEPENDE_DE", "Depende de"
    ORIGINATED = "ORIGINOU", "Originou"
    INSPIRED = "INSPIROU", "Inspirou"
    PARTICIPATES = "PARTICIPA_DE", "Participa de"
    RESOLVES = "RESOLVE", "Resolve"
    ANSWERS = "RESPONDE", "Responde"
    AFFECTS = "AFETA", "Afeta"
    GENERATED = "GEROU", "Gerou"
    LEARNED_FROM = "APRENDEU_COM", "Aprendeu com"


class RelationshipManager(models.Manager.from_queryset(KnowledgeQuerySet)):
    pass


class Relationship(AtlasModel, OwnerMixin):
    """Uma aresta orientada origin → target com um tipo.

    `origin` e `target` são GenericForeignKey para entidades do Knowledge Core.
    """

    type = models.CharField(max_length=40, choices=RelationshipType.choices)

    # --- Origin (ponto de partida da aresta) ---
    origin_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
    )
    origin_id = models.UUIDField()
    origin = GenericForeignKey("origin_type", "origin_id")

    # --- Target (ponto de chegada da aresta) ---
    target_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
    )
    target_id = models.UUIDField()
    target = GenericForeignKey("target_type", "target_id")

    objects = RelationshipManager()

    class Meta:
        verbose_name = "Relacionamento"
        verbose_name_plural = "Relacionamentos"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["origin_type", "origin_id", "target_type", "target_id", "type"],
                name="unique_relationship",
            )
        ]

    def __str__(self):
        return f"{self.origin} --{self.type}--> {self.target}"

    @classmethod
    def eligible_content_types(cls):
        """ContentTypes das entidades aptas a participar de relacionamentos."""
        for app_label, model_name in getattr(settings, "RELATIONSHIP_MODELS", []):
            try:
                yield ContentType.objects.get_by_natural_key(app_label, model_name)
            except ContentType.DoesNotExist:
                continue

    @classmethod
    def eligible_model_names(cls):
        return set(settings.RELATIONSHIP_MODELS)
