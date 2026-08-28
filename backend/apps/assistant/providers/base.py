"""Abstração do provedor de IA.

Toda a lógica de negócio do Atlas (RAG, tools, memória, contexto, agentes)
depende APENAS desta interface - nunca do SDK de um provedor específico.

Para adicionar um novo provedor no futuro, basta implementar esta interface
sem alterar as camadas superiores.

FASE 5 implementará GeminiProvider (apps/assistant/providers/gemini.py).
Este módulo define apenas o CONTRATO na FASE 1.
"""

from abc import ABC, abstractmethod
from typing import Any, Iterable


class AIProvider(ABC):
    """Contrato mínimo de um provedor de IA (chat + embeddings)."""

    @abstractmethod
    def generate_text(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: Iterable[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Gera uma resposta de texto.

        `messages`: lista de mensagens no formato [{"role", "content"}, ...].
        `tools`:   definições de function calling (opcional).
        Retorna um dicionário contendo ao menos 'content' e, quando houver,
        'tool_calls'.
        """

    @abstractmethod
    def embed_text(self, text: str, **kwargs: Any) -> list[float]:
        """Retorna o vetor de embeddings de um texto."""

    @abstractmethod
    def embed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """Retorna os vetores de embeddings de vários textos."""
