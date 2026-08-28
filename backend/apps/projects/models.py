"""Entidade Project — um projeto.

Possui nome, descrição, objetivo, status, tecnologias e pode ter origem em
uma ou mais Ideias. Relações com conhecimento/decisões/experiências serão
consolidadas pela rede de relacionamentos (Fase 3).
"""

from django.db import models

from apps.core.models import KnowledgeEntity, Status


class Project(KnowledgeEntity):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    objective = models.TextField(blank=True)
    technologies = models.JSONField(default=list, blank=True)

    class Meta(KnowledgeEntity.Meta):
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Mantém `title` sincronizado com `name` para compatibilidade da base.
        if not self.title:
            self.title = self.name
        super().save(*args, **kwargs)

    def active_ideas(self):
        return self.source_ideas.filter(deleted_at__isnull=True)
