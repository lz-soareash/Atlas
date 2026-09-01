"""Cognitive Engine — ContextManager e CognitiveService (Fase 10).

Objetivo: expor ao Jarvis (integração serviço→serviço) uma API estável de
RACIOCÍNIO sobre o conhecimento do Atlas, com sessões persistentes e respostas
estruturadas — REUTILIZANDO toda a infraestrutura existente (retrieval,
provider de IA, classificação), sem duplicar nem quebrar o que já existe.

Regras:
- Leitura apenas (análise/raciocínio). NUNCA executa tools de escrita; assim a
  integração externa não pode contornar a aprovação via ToolProposal.
- Fallback de provider (Gemini → DeterministicProvider) já resolvido em
  `resolve_chat_provider`.
- Observabilidade via AuditLog (sem secrets) feita na camada de views.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from apps.assistant.exceptions import AIError
from apps.assistant.prompts import CONTEXT_PROMPT, SYSTEM_PROMPT
from apps.assistant.providers import resolve_chat_provider
from apps.assistant.services.chat import parse_classification
from apps.assistant.services.context import build_context

from .models import CognitiveSession, SessionMessage

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

MAX_CONTEXT_MESSAGES = 12


class ContextManager:
    """Monta o contexto de uma pergunta, somando a sessão cognitiva."""

    def build(self, owner, session: CognitiveSession | None, query: str) -> dict:
        """Combina o retrieval padrão com o project_context da sessão."""
        try:
            context = build_context(owner, query)
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao montar contexto cognitivo")
            context = {"query": query, "sources": [], "graph_edges": [], "memories": []}

        session_context = {}
        if session is not None and session.project_context:
            session_context = {
                "project_context": session.project_context,
                "session_id": str(session.pk),
                "session_name": session.name,
            }
        context["session"] = session_context
        context["semantic_available"] = bool(
            context.get("semantic_available", False)
        )
        return context


class CognitiveService:
    """Raciocínio estruturado e read-only sobre o conhecimento do Atlas."""

    def __init__(self, provider=None):
        self._provider = provider

    @property
    def provider(self):
        if self._provider is None:
            self._provider = resolve_chat_provider()
        return self._provider

    def reason(
        self,
        owner,
        session: CognitiveSession | None,
        query: str,
        *,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Gera uma resposta estruturada para `query` na `session`.

        Retorna {answer, sources, classification, provider, semantic_available}.
        A sessão e o histórico são persistidos pela camada de views para manter
        o CognitiveService simples e testável.
        """
        query = (query or "").strip()
        if not query:
            raise AIError(detail="Consulta vazia.")

        context = ContextManager().build(owner, session, query)
        messages = self._build_provider_messages(query, context, history or [])

        try:
            result = self.provider.generate_text(
                messages,
                context=context,
                temperature=0.3,
            )
        except AIError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Cognitive reason falhou")
            raise AIError(detail=str(exc)) from exc

        answer = (result.get("content") or "").strip()
        if not answer:
            answer = "Não consegui gerar uma análise para esta consulta."
            classification = {
                "kind": "sugestao",
                "label": "Sugestão (sem fontes no Atlas)",
                "source_based": False,
            }
        else:
            answer, classification = parse_classification(
                answer, has_sources=bool(context["sources"])
            )

        return {
            "answer": answer,
            "sources": self._sources_public(context["sources"]),
            "classification": classification,
            "provider": self._provider_name(),
            "semantic_available": context.get("semantic_available", False),
        }

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    def _build_provider_messages(self, query, context, history) -> list[dict]:
        context_block = CONTEXT_PROMPT.format(
            sources_block=self._serialize_sources(context["sources"]),
            graph_block=self._serialize_graph(context.get("graph_edges", [])),
            memory_block=self._serialize_memories(context.get("memories", [])),
        )
        project_block = self._serialize_project_context(context.get("session"))
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": context_block},
        ]
        if project_block:
            messages.append({"role": "system", "content": project_block})
        messages.extend(history[-MAX_CONTEXT_MESSAGES:])
        messages.append({"role": "user", "content": query})
        return messages

    @staticmethod
    def _serialize_project_context(session) -> str:
        ctx = (session or {}).get("project_context") or {}
        if not ctx:
            return ""
        lines = ["\nContexto do projeto (sessão cognitiva):"]
        for k, v in list(ctx.items())[:12]:
            cap = k.replace("_", " ").capitalize()
            lines.append(f"- {cap}: {v}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _serialize_memories(memories) -> str:
        if not memories:
            return ""
        lines = ["\nMemórias do usuário (preferências, contexto e objetivos):"]
        for m in memories[:8]:
            lines.append(f"- ({m.get('label', '')}) {m.get('content', '')}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _serialize_sources(sources) -> str:
        if not sources:
            return "(Nenhuma fonte encontrada no Atlas.)"
        lines = []
        for i, s in enumerate(sources, start=1):
            emoji = _SOURCE_EMOJI.get(s.get("entity"), "•")
            kind = s.get("label", s.get("entity", ""))
            status = s.get("status") or ""
            lines.append(
                f"[{i}] {emoji} {kind}: {s.get('title', '')}"
                f" (status: {status})\n    {s.get('snippet', '')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _serialize_graph(edges) -> str:
        if not edges:
            return ""
        lines = ["Fonte — relacionamentos do grafo:"]
        for e in edges:
            lines.append(f"- {e.get('origin')} {e.get('type')} → {e.get('target')}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _sources_public(sources) -> list[dict]:
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

    def _provider_name(self) -> str:
        name = self.provider.__class__.__name__.lower()
        return "gemini" if "gemini" in name else "deterministic"

    # ------------------------------------------------------------------ #
    # persistência de histórico (usada pelas views)
    # ------------------------------------------------------------------ #

    def save_turn(self, owner, session: CognitiveSession, query: str, result: dict):
        """Persiste o turno (pergunta + resposta) no histórico da sessão."""
        SessionMessage.objects.create(
            owner=owner, session=session, role="user", content=query, sources=[]
        )
        SessionMessage.objects.create(
            owner=owner,
            session=session,
            role="assistant",
            content=result["answer"],
            sources=result["sources"],
        )
        session.save(update_fields=["updated_at"])

    def history(self, session: CognitiveSession) -> list[dict]:
        """Histórico da sessão no formato esperado pelo provider."""
        msgs = []
        for m in SessionMessage.objects.filter(session=session).order_by("created_at"):
            msgs.append({"role": m.role, "content": m.content})
        return msgs[-MAX_CONTEXT_MESSAGES:]
