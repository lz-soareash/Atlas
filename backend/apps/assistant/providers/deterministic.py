"""DeterministicProvider — fallback offline (sem LLM).

Usado quando não há GEMINI_API_KEY (modo determinístico) e em testes.
Não faz chamada externa: monta uma resposta a partir do contexto já
recuperado pelo serviço de chat, citando as fontes de forma rastreável.

`available()` sempre True, pois não depende de infraestrutura externa.
"""

from __future__ import annotations

from typing import Any, Iterable

from .base import AIProvider
from ..exceptions import ProviderUnavailableError

_SOURCE_LABEL = {
    "knowledge": "🧠 Conhecimento",
    "idea": "💡 Ideia",
    "project": "📁 Projeto",
    "question": "❓ Pergunta",
    "decision": "⚖️ Decisão",
    "experience": "📝 Experiência",
    "relationship": "🔗 Relacionamento",
}


class DeterministicProvider(AIProvider):
    """Resposta determinística a partir do contexto (modo offline/fallback)."""

    def available(self) -> bool:
        return True

    def generate_text(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: Iterable[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if "raise_unavailable" in kwargs:
            raise ProviderUnavailableError()
        return {"content": self._answer(messages, kwargs), "tool_calls": []}

    def _last_user(self, messages):
        for msg in reversed(messages):
            if msg.get("role") == "user" and msg.get("content"):
                return msg["content"]
        return ""

    def _answer(self, messages, kwargs):
        context = kwargs.get("context") or {}
        query = self._last_user(messages)
        sources = context.get("sources", [])

        if not sources:
            return (
                "Modo determinístico (sem LLM configurado). "
                "Nenhuma fonte encontrada no Atlas para: “%s”." % (query or "sua pergunta")
            )

        lines = [f"Encontrei {len(sources)} fonte(s) no Atlas para “{query or 'sua pergunta'}”:"]
        for s in sources[:6]:
            label = _SOURCE_LABEL.get(s.get("entity"), s.get("entity", "fonte"))
            lines.append(f"- {label}: {s.get('title', '')}")
        lines.append("")
        lines.append(
            "Este é o modo determinístico (sem GEMINI_API_KEY). "
            "Configure uma chave para respostas completas via Gemini."
        )
        return "\n".join(lines)

    def embed_text(self, text: str, **kwargs: Any) -> list[float]:
        from apps.search.embeddings import FingerprintEmbeddingProvider

        return FingerprintEmbeddingProvider().embed_documents([text])[0]

    def embed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        from apps.search.embeddings import FingerprintEmbeddingProvider

        return FingerprintEmbeddingProvider().embed_documents(texts)
