"""Entidade Question — algo que o usuário ainda não sabe.

Uma pergunta pode gerar um Conhecimento (transformação).
"""

from django.db import models

from apps.core.models import KnowledgeEntity, Status


class Question(KnowledgeEntity):
    question_text = models.TextField(blank=True)
    answered = models.BooleanField(default=False)
    # Conhecimento originado (preenchido quando respondida/convertida).
    knowledge = models.ForeignKey(
        "knowledge.Knowledge",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_questions",
    )

    class Meta(KnowledgeEntity.Meta):
        verbose_name = "Pergunta"
        verbose_name_plural = "Perguntas"

    def answer(self, knowledge):
        """Marca a pergunta como respondida com o conhecimento dado."""
        self.answered = True
        self.status = Status.COMMITTED
        self.knowledge = knowledge
        self.save()
