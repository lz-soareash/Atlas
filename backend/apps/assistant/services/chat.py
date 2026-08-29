"""ChatService — orquestração do chat com RAG básico (Fase 5).

Fluxo: mensagens → validação/limite → retrieval (context) → prompt →
provider (Gemini ou fallback determinístico) → resposta com fontes e
classificação.

O ChatService é agnóstico de provedor: depende apenas do AIProvider.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

from apps.assistant.exceptions import AIError, RateLimitExceededError, TokenLimitError
from apps.assistant.models import ProposalStatus, ToolProposal
from apps.assistant.prompts import CONTEXT_PROMPT, SYSTEM_PROMPT
from apps.assistant.providers import resolve_chat_provider
from apps.assistant.serializers import ToolProposalSerializer
from apps.assistant.tools import (
    PROPOSAL_TOOLS,
    all_tool_definitions,
    dispatch_execution,
    get_tool_definition,
)
from apps.assistant.tools.exceptions import ToolError
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

# Tags de classificação exigidas do modelo (ver prompts.SYSTEM_PROMPT).
_CLASSIFICATION_TAGS = {
    "[FATO]": ("fato", "Fato (com base no Atlas)", True),
    "[INFERÊNCIA]": ("inferencia", "Inferência (conclusão da IA)", True),
    "[SUGESTÃO]": ("sugestao", "Sugestão (recomendação da IA)", False),
    "[INFORMAÇÃO EXTERNA]": ("informacao_externa", "Informação externa (fora do Atlas)", False),
}


def parse_classification(answer: str, *, has_sources: bool) -> tuple[str, dict]:
    """Extrai a tag de classificação do início da resposta.

    Se o modelo não seguir o formato, cai para a heurística: com fontes →
    Fato; sem fontes → Sugestão.
    Returns (answer_sem_tag, classification).
    """
    stripped = answer.lstrip()
    for tag, (kind, label, _) in _CLASSIFICATION_TAGS.items():
        if stripped.startswith(tag):
            remainder = stripped[len(tag):].lstrip()
            source_based = kind in ("fato", "inferencia") and has_sources
            return remainder, {"kind": kind, "label": label, "source_based": source_based}

    if has_sources:
        return answer, {"kind": "fato", "label": "Fato (com base no Atlas)", "source_based": True}
    return answer, {"kind": "sugestao", "label": "Sugestão (sem fontes no Atlas)", "source_based": False}


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

        tools = all_tool_definitions()
        proposals = []
        try:
            result = self.provider.generate_text(
                provider_messages,
                context=context,
                temperature=0.4,
                tools=tools,
            )
        except RateLimitExceededError:
            raise
        except AIError as exc:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Chat falhou")
            raise AIError(detail=str(exc)) from exc

        # ----- Tools (Fase 7) -----
        # Se o modelo pediu tools, executa leitura / cria propostas de escrita
        # e, para leitura, faz uma segunda chamada com os resultados.
        tool_calls = result.get("tool_calls") or []
        if tool_calls:
            tool_results, proposals = self._process_tool_calls(owner, tool_calls, context)
            if tool_results:
                provider_messages = provider_messages + self._tool_result_messages(tool_results)
                try:
                    result = self.provider.generate_text(
                        provider_messages,
                        context=context,
                        temperature=0.4,
                        tools=tools,
                    )
                except AIError as exc:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Chat (tools) falhou")
                    raise AIError(detail=str(exc)) from exc

        answer = result.get("content", "").strip()
        if not answer and not proposals:
            answer = "Não consegui gerar uma resposta. Tente novamente."
            classification = {"kind": "sugestao", "label": "Sugestão (sem fontes no Atlas)", "source_based": False}
        elif not answer:
            answer = "Posso criar o que você pediu. Confirme abaixo para eu registrar no Atlas."
            classification = {"kind": "sugestao", "label": "Sugestão (aguarda confirmação)", "source_based": False}
        else:
            answer, classification = parse_classification(answer, has_sources=bool(context["sources"]))

        return {
            "answer": answer,
            "sources": self._sources_public(context["sources"]),
            "provider": self._provider_name(),
            "classification": classification,
            "semantic_available": context.get("semantic_available", False),
            "proposals": ToolProposalSerializer(proposals, many=True).data if proposals else [],
        }

    # --- helpers ---

    def _process_tool_calls(self, owner, tool_calls, context):
        """Processa as tools pedidas pelo modelo.

        Leitura → executa e retorna resultados para a segunda chamada.
        Escrita → gera uma ToolProposal pendente para confirmação do usuário.
        """
        tool_results = []  # [{"tool_call_id", "name", "content": json}]
        proposals = []
        for call in tool_calls:
            name = call.get("name")
            args = call.get("args") or {}
            spec = get_tool_definition(name)

            if spec is None:
                tool_results.append({"name": name, "content": json.dumps({"error": "tool desconhecida"})})
                continue

            if spec["kind"] == "write" and name in PROPOSAL_TOOLS:
                try:
                    normalized = spec["handler"](owner, **args)
                    proposal = self._create_proposal(owner, name, normalized, context)
                    proposals.append(proposal)
                    tool_results.append(
                        {
                            "name": name,
                            "content": json.dumps(
                                {
                                    "proposal_id": str(proposal.pk),
                                    "status": proposal.status,
                                    "created": False,
                                    "message": "Proposta criada; aguardando confirmação do usuário.",
                                }
                            ),
                        }
                    )
                except ToolError as exc:
                    tool_results.append({"name": name, "content": json.dumps({"error": exc.user_message})})
                continue

            # Leitura: executa agora.
            try:
                result = dispatch_execution(owner, name, args)
                tool_results.append({"name": name, "content": json.dumps(result)})
            except ToolError as exc:
                tool_results.append({"name": name, "content": json.dumps({"error": exc.user_message})})
            except Exception as exc:  # noqa: BLE001
                logger.exception("Tool %s falhou", name)
                tool_results.append({"name": name, "content": json.dumps({"error": "erro interno"})})

        return tool_results, proposals

    def _create_proposal(self, owner, tool_name, normalized, context) -> ToolProposal:
        entity = normalized.get("entity", "")
        payload = normalized.get("payload", {})
        summary = self._proposal_summary(entity, payload)
        return ToolProposal.objects.create(
            owner=owner,
            tool=tool_name,
            entity=entity,
            summary=summary,
            payload=payload,
            status=ProposalStatus.PENDING,
        )

    def _proposal_summary(self, entity: str, payload: dict) -> str:
        title = payload.get("title") or payload.get("name") or ""
        if entity == "relationship":
            origin = (payload.get("origin") or {}).get("entity", "?")
            target = (payload.get("target") or {}).get("entity", "?")
            return f"{payload.get('type', '')}: {origin} → {target}"
        return f"{entity}: {title}".strip()

    def _tool_result_messages(self, tool_results) -> list[dict]:
        msgs = []
        for tr in tool_results:
            msgs.append({"role": "tool", "name": tr["name"], "content": tr["content"]})
        return msgs

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
            memory_block=self._serialize_memories(context.get("memories", [])),
        )
        provider_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": context_block},
        ]
        provider_messages.extend(messages)
        return provider_messages

    def _serialize_memories(self, memories) -> str:
        if not memories:
            return ""
        lines = ["\nMemórias do usuário (preferências, contexto e objetivos):"]
        for m in memories[:8]:
            lines.append(f"- ({m.get('label', '')}) {m.get('content', '')}")
        return "\n".join(lines) + "\n"

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
