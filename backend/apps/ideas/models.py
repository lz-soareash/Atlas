"""Entidade Idea — uma ideia.

Ex.: site para Grêmio, novo projeto, funcionalidade, conceito.
Uma ideia pode evoluir para um Projeto (transformação registrada).
"""

from django.db import models

from apps.core.models import KnowledgeEntity, Status


class Idea(KnowledgeEntity):
    description = models.TextField(blank=True)
    # Marca a transformação: esta ideia deu origem a um Projeto.
    converted = models.BooleanField(default=False)
    # Referência ao projeto originado (preenchida na conversão).
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_ideas",
    )

    class Meta(KnowledgeEntity.Meta):
        verbose_name = "Ideia"
        verbose_name_plural = "Ideias"

    def convert_to_project(self, *, name, description="", objective="", technologies=None):
        """Transforma esta ideia em um Projeto, registrando a origem.

        Importa o modelo de projetos sob demanda (evita import circular).
        """
        from apps.projects.models import Project

        project = Project.objects.create(
            owner=self.owner,
            name=name or self.title,
            description=description or self.description,
            objective=objective,
            technologies=technologies or [],
            status=Status.ACTIVE,
        )
        self.converted = True
        self.status = Status.COMMITTED
        self.project = project
        self.save()
        return project
