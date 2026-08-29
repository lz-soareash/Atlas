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
from apps.assistant.models import AgentRun, AgentRunStatus, ProposalStatus, ToolProposal
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

        # ----- Tools / Agente (Fase 7 + Fase 9) -----
        # Se o modelo pediu tools, executa um loop de agente: processa as calls,
        # devolve os resultados à IA e repete até não haver mais calls (ou
        # atingir MAX_TOOL_ITERATIONS). Leitura executa na hora; escrita sempre
        # gera ToolProposal pendente (execução controlada). Cada passo é
        # registrado num AgentRun transparente.
        proposals = []
        agent_run = None
        tool_calls = result.get("tool_calls") or []
        if tool_calls:
            agent_run, result, proposals = self._agent_loop(owner, provider_messages, context, tool_calls)

        answer = result.get("content", "").strip()
        if not answer and not proposals:
            answer = "Não consegui gerar uma resposta. Tente novamente."
            classification = {"kind": "sugestao", "label": "Sugestão (sem fontes no Atlas)", "source_based": False}
        elif not answer:
            answer = "Posso criar o que você pediu. Confirme abaixo para eu registrar no Atlas."
            classification = {"kind": "sugestao", "label": "Sugestão (aguarda confirmação)", "source_based": False}
        else:
            answer, classification = parse_classification(answer, has_sources=bool(context["sources"]))

        response_data = {
            "answer": answer,
            "sources": self._sources_public(context["sources"]),
            "provider": self._provider_name(),
            "classification": classification,
            "semantic_available": context.get("semantic_available", False),
            "proposals": ToolProposalSerializer(proposals, many=True).data if proposals else [],
        }
        if agent_run is not None:
            response_data["agent_run"] = {
                "id": str(agent_run.pk),
                "query": agent_run.query,
                "status": agent_run.status,
                "iterations": agent_run.iterations,
                "steps": agent_run.steps,
                "created_at": agent_run.created_at.isoformat() if agent_run.created_at else None,
            }
        return response_data

    def _agent_loop(self, owner, provider_messages, context, initial_tool_calls):
        """Loop de agente: executa tools, devolve resultados e repete.

        Escritas viram ToolProposal (nunca executadas no loop). Leitura executa.
        Retorna (AgentRun, resultado_final, proposals).
        """
        max_iterations = getattr(settings, "MAX_TOOL_ITERATIONS", 6)
        tools = all_tool_definitions()
        messages = list(provider_messages)
        proposals = []
        all_steps = []
        iteration = 0
        tool_calls = initial_tool_calls
        result = None

        run = AgentRun.objects.create(
            owner=owner,
            query=self._calls_preview(initial_tool_calls),
            status=AgentRunStatus.RUNNING,
            steps=[],
        )

        while tool_calls and iteration < max_iterations:
            iteration += 1
            tool_results, new_proposals, steps = self._process_tool_calls(owner, tool_calls, context, iteration)
            all_steps.extend(steps)
            proposals.extend(new_proposals)
            if tool_results:
                messages = messages + self._tool_result_messages(tool_results)
            try:
                result = self.provider.generate_text(
                    messages,
                    context=context,
                    temperature=0.4,
                    tools=tools,
                )
            except AIError:
                self._finish_run(run, AgentRunStatus.ERROR, all_steps, iteration)
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("Chat (agente) falhou")
                self._finish_run(run, AgentRunStatus.ERROR, all_steps, iteration)
                raise AIError(detail=str(exc)) from exc
            tool_calls = result.get("tool_calls") or []

        if result is None:
            result = {"content": "", "tool_calls": []}

        run.iterations = iteration
        run.steps = all_steps
        run.status = AgentRunStatus.DONE
        run.save(update_fields=["iterations", "steps", "status", "updated_at"])

        # Escreve de volta o run (steps já persistidos) para o caller reportar.
        return run, result, proposals

    @staticmethod
    def _finish_run(run, status, steps, iterations):
        try:
            run.iterations = iterations
            run.steps = steps
            run.status = status
            run.save(update_fields=["iterations", "steps", "status", "updated_at"])
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao gravar AgentRun")

    @staticmethod
    def _calls_preview(tool_calls) -> str:
        parts = []
        for call in tool_calls or []:
            parts.append(str(call.get("name", "?")))
        return ", ".join(parts)[:500] or "(sem tool calls)"

    def _process_tool_calls(self, owner, tool_calls, context, iteration: int):
        """Processa as tools pedidas pelo modelo; retorna resultados + steps.

        Leitura → executa e retorna resultados para a próxima iteração.
        Escrita → gera uma ToolProposal pendente para confirmação do usuário.
        """
        tool_results = []  # [{"tool_call_id", "name", "content": json}]
        proposals = []
        steps = []  # [{"iteration", "tool", "kind", "status", "summary"}]
        for call in tool_calls:
            call_id = call.get("id") or f"{call.get('name', 'tool')}-{len(steps)}"
            name = call.get("name")
            args = call.get("args") or {}
            spec = get_tool_definition(name)

            if spec is None:
                tool_results.append(
                    {"tool_call_id": call_id, "name": name, "content": json.dumps({"error": "tool desconhecida"})}
                )
                steps.append({"iteration": iteration, "tool": name, "kind": spec and spec.get("kind"), "status": "error", "summary": "tool desconhecida"})
                continue

            if spec["kind"] == "write" and name in PROPOSAL_TOOLS:
                try:
                    normalized = spec["handler"](owner, **args)
                    proposal = self._create_proposal(owner, name, normalized, context)
                    proposals.append(proposal)
                    tool_results.append(
                        {
                            "tool_call_id": call_id,
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
                    steps.append(
                        {
                            "iteration": iteration,
                            "tool": name,
                            "kind": "write",
                            "status": "ok",
                            "summary": f"Proposta ({proposal.get_status_display()}): {proposal.summary}",
                        }
                    )
                except ToolError as exc:
                    tool_results.append({"tool_call_id": call_id, "name": name, "content": json.dumps({"error": exc.user_message})})
                    steps.append(
                        {"iteration": iteration, "tool": name, "kind": "write", "status": "error", "summary": exc.user_message}
                    )
                continue

            # Leitura: executa agora.
            try:
                result = dispatch_execution(owner, name, args)
                tool_results.append({"tool_call_id": call_id, "name": name, "content": json.dumps(result)})
                steps.append(
                    {"iteration": iteration, "tool": name, "kind": "read", "status": "ok", "summary": self._read_step_summary(result)}
                )
            except ToolError as exc:
                tool_results.append({"tool_call_id": call_id, "name": name, "content": json.dumps({"error": exc.user_message})})
                steps.append(
                    {"iteration": iteration, "tool": name, "kind": "read", "status": "error", "summary": exc.user_message}
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Tool %s falhou", name)
                tool_results.append({"tool_call_id": call_id, "name": name, "content": json.dumps({"error": "erro interno"})})
                steps.append(
                    {"iteration": iteration, "tool": name, "kind": "read", "status": "error", "summary": "erro interno"}
                )

        return tool_results, proposals, steps

    @staticmethod
    def _read_step_summary(result: dict) -> str:
        """Resumo humano de um resultado de tool de leitura."""
        if isinstance(result, dict) and "results" in result:
            return f"{len(result['results'])} resultado(s)"
        if isinstance(result, dict) and "related" in result:
            return f"{len(result['related'])} relacionados"
        if isinstance(result, dict) and isinstance(result.get("project"), dict):
            return f"projeto: {result['project'].get('title', '')}"
        if isinstance(result, dict) and result.get("id"):
            return f"entidade {result.get('entity')}: {result.get('title', '')}"
        return "leitura concluída"

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
            msg = {"role": "tool", "name": tr["name"], "content": tr["content"]}
            if tr.get("tool_call_id"):
                msg["tool_call_id"] = tr["tool_call_id"]
            msgs.append(msg)
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
