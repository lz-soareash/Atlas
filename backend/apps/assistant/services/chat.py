"""ChatService — orquestração do chat com RAG básico (Fase 5).

Fluxo: mensagens → validação/limite → retrieval (context) → prompt →
provider (Gemini ou fallback determinístico) → resposta com fontes e
classificação.

O ChatService é agnóstico de provedor: depende apenas do AIProvider.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from apps.assistant.exceptions import AIError, RateLimitExceededError, TokenLimitError
from apps.assistant.providers import resolve_chat_provider
from apps.assistant.prompts import CONTEXT_PROMPT, SYSTEM_PROMPT
from apps.search.service import SEARCH_ENTITIES

from .context import build_context

logger = logging.getLogger(__name__)

_SOURCE_EMOJI = {
    "knowledge": "🧠",
    "idea": "💡",
    "project": "📁",
    "question": "❓",
    "decision": "⚖️",
    "experience": "📝",
    "relationship": "🔗",
}
_TYPE_NAMES = {m["key"]: m["label"] for m in SEARCH_ENTITIES}


class ChatService:
    """Processa uma conversa de chat do usuário com o Atlas."""

    def __init__(self, provider=None):
        self._provider = provider

    @property
    def provider(self):
        if self._provider is None:
            self._provider = resolve_chat_provider()
        return self._provider

    def chat(self, owner, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Recebe o histórico, retorna {answer, sources, provider, classification}."""
        messages = self._sanitize_messages(messages)
        if not messages:
            raise AIError(detail="Mensagens vazias.")

        query = self._last_user(messages)

        # Rei-valida o rate limit no nível de serviço (cache backend), além do
        # throttle HTTP — para cobrir qualquer entrada.
        try:
            context = build_context(owner, query)
        except Exception:  # pragma: no cover
            logger.exception("Falha ao montar contexto")
            context = {"query": query, "sources": [], "graph_edges": []}

        provider_messages = self._build_provider_messages(messages, context)

        try:
            result = self.provider.generate_text(
                provider_messages,
                context=context,
                temperature=0.4,
            )
        except RateLimitExceededError:
            raise
        except AIError as exc:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Chat falhou")
            raise AIError(detail=str(exc)) from exc

        answer = result.get("content", "").strip()
        if not answer:
            answer = "Não consegui gerar uma resposta. Tente novamente."

        return {
            "answer": answer,
            "sources": self._sources_public(context["sources"]),
            "provider": self._provider_name(),
            "classification": self._classify(context["sources"]),
            "semantic_available": context.get("semantic_available", False),
        }

    # --- helpers ---

    def _provider_name(self) -> str:
        name = self.provider.__class__.__name__.lower()
        return "gemini" if "gemini" in name else "deterministic"

    def _sanitize_messages(self, messages) -> list[dict]:
        limit = getattr(settings, "MAX_CHAT_MESSAGES", 24)
        clean = []
        text_total = 0
        for msg in messages or []:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            content = str(msg.get("content", "")).strip()
            if role not in ("user", "assistant") or not content:
                continue
            if content == "__atlas_system_note__":  # reservado
                continue
            clean.append({"role": role, "content": content})
            text_total += len(content)
        if text_total > 12000:  # proteção de tamanho
            raise TokenLimitError()
        return clean[-limit:]

    def _last_user(self, messages) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return msg["content"]
        return ""

    def _build_provider_messages(self, messages, context) -> list[dict]:
        context_block = CONTEXT_PROMPT.format(
            sources_block=self._serialize_sources(context["sources"]),
            graph_block=self._serialize_graph(context.get("graph_edges", [])),
        )
        provider_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": context_block},
        ]
        provider_messages.extend(messages)
        return provider_messages

    def _serialize_sources(self, sources) -> str:
        if not sources:
            return "(Nenhuma fonte encontrada no Atlas.)"
        lines = []
        for i, s in enumerate(sources, start=1):
            emoji = _SOURCE_EMOJI.get(s.get("entity"), "•")
            kind = _TYPE_NAMES.get(s.get("entity"), s.get("label", ""))
            status = s.get("status") or ""
            lines.append(
                f"[{i}] {emoji} {kind}: {s.get('title', '')}"
                f" (status: {status})\n    {s.get('snippet', '')}"
            )
        return "\n".join(lines)

    def _serialize_graph(self, edges) -> str:
        if not edges:
            return ""
        lines = ["Fonte — relacionamentos do grafo:"]
        for e in edges:
            lines.append(f"- {e.get('origin')} {e.get('type')} → {e.get('target')}")
        return "\n".join(lines) + "\n"

    def _sources_public(self, sources) -> list[dict]:
        return [
            {
                "id": s.get("id"),
                "entity": s.get("entity"),
                "label": s.get("label"),
                "title": s.get("title"),
                "route": s.get("route"),
                "score": s.get("score"),
            }
            for s in sources
        ]

    def _classify(self, sources) -> dict:
        if sources:
            return {"kind": "fato", "label": "Fato (com base no Atlas)", "source_based": True}
        return {"kind": "sugestao", "label": "Sugestão (sem fontes no Atlas)", "source_based": False}
