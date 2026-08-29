"""Registro central de tools do Atlas Assistant.

Cada tool tem:
- `name`: nome usado pelo modelo (function calling).
- `args`: schema (dicionário {campo: {type, description, required}}).
- `kind`: "read" (execução imediata) ou "write" (gera ToolProposal).
- `handler`: função `(owner, **args) -> dict` que valida ownership/permissões.
"""

from __future__ import annotations

from apps.assistant.tools import read, write
from apps.assistant.tools.exceptions import ToolNotFoundError

# Leitura: segura, executada imediatamente pelo serviço.
READ_TOOLS = {
    "search_entities": {
        "description": "Busca híbrida nas entidades do usuário (conhecimento, ideia, projeto, pergunta, decisão, experiência). Retorna itens com id, entity, title, snippet, score.",
        "kind": "read",
        "handler": read.search_entities,
        "args": {
            "query": {"type": "string", "description": "Termo(s) de busca", "required": True},
            "type": {"type": "string", "description": "Filtrar por entidade (opcional)", "required": False},
            "limit": {"type": "integer", "description": "Máx. de resultados (1-20)", "required": False},
        },
    },
    "get_entity": {
        "description": "Retorna os detalhes completos de uma entidade específica do usuário por entity+id",
        "kind": "read",
        "handler": read.get_entity,
        "args": {
            "entity": {"type": "string", "description": "Tipo: knowledge, idea, project, question, decision, experience", "required": True},
            "id": {"type": "string", "description": "UUID da entidade", "required": True},
        },
    },
    "get_project_context": {
        "description": "Retorna um projeto do usuário e as ideias que o originaram",
        "kind": "read",
        "handler": read.get_project_context,
        "args": {
            "id": {"type": "string", "description": "UUID do projeto", "required": True},
        },
    },
    "find_related_entities": {
        "description": "Encontra entidades relacionadas (grafo) a uma entidade do usuário",
        "kind": "read",
        "handler": read.find_related_entities,
        "args": {
            "entity": {"type": "string", "description": "Tipo da entidade de origem", "required": True},
            "id": {"type": "string", "description": "UUID da entidade de origem", "required": True},
        },
    },
}

# Escrita: NUNCA executada direto — geram ToolProposal para confirmação.
WRITE_TOOLS = {
    "create_idea": {
        "description": "Propor a criação de uma Ideia (exige confirmação do usuário)",
        "kind": "write",
        "handler": write.create_idea,
        "args": {
            "title": {"type": "string", "description": "Título da ideia", "required": True},
            "description": {"type": "string", "description": "Descrição", "required": False},
            "summary": {"type": "string", "description": "Resumo", "required": False},
        },
    },
    "create_question": {
        "description": "Propor a criação de uma Pergunta (exige confirmação)",
        "kind": "write",
        "handler": write.create_question,
        "args": {
            "title": {"type": "string", "description": "Pergunta", "required": True},
            "question_text": {"type": "string", "description": "Detalhes", "required": False},
        },
    },
    "create_knowledge": {
        "description": "Propor a criação de um Conhecimento (exige confirmação)",
        "kind": "write",
        "handler": write.create_knowledge,
        "args": {
            "title": {"type": "string", "description": "Título", "required": True},
            "content": {"type": "string", "description": "Conteúdo", "required": False},
            "summary": {"type": "string", "description": "Resumo", "required": False},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags", "required": False},
        },
    },
    "create_project": {
        "description": "Propor a criação de um Projeto (exige confirmação)",
        "kind": "write",
        "handler": write.create_project,
        "args": {
            "name": {"type": "string", "description": "Nome do projeto", "required": True},
            "objective": {"type": "string", "description": "Objetivo", "required": False},
            "description": {"type": "string", "description": "Descrição", "required": False},
            "technologies": {"type": "array", "items": {"type": "string"}, "description": "Tecnologias", "required": False},
        },
    },
    "create_decision": {
        "description": "Propor o registro de uma Decisão (exige confirmação)",
        "kind": "write",
        "handler": write.create_decision,
        "args": {
            "title": {"type": "string", "description": "Título", "required": True},
            "context": {"type": "string", "description": "Contexto", "required": False},
            "problem": {"type": "string", "description": "Problema", "required": False},
            "decision": {"type": "string", "description": "Decisão", "required": False},
            "rationale": {"type": "string", "description": "Justificativa", "required": False},
            "alternatives": {"type": "array", "items": {"type": "string"}, "description": "Alternativas", "required": False},
        },
    },
    "create_experience": {
        "description": "Propor o registro de uma Experiência (exige confirmação)",
        "kind": "write",
        "handler": write.create_experience,
        "args": {
            "title": {"type": "string", "description": "Título", "required": True},
            "content": {"type": "string", "description": "Conteúdo", "required": False},
            "kind": {"type": "string", "description": "error|solution|discovery|experiment|lesson", "required": False},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags", "required": False},
        },
    },
    "create_relationship": {
        "description": "Propor a criação de um relacionamento entre duas entidades (exige confirmação)",
        "kind": "write",
        "handler": write.create_relationship,
        "args": {
            "type": {"type": "string", "description": "Tipo do relacionamento (ex.: USA, DEPENDE_DE)", "required": True},
            "origin": {"type": "object", "properties": {"entity": {"type": "string"}, "id": {"type": "string"}}, "description": "Entidade de origem", "required": True},
            "target": {"type": "object", "properties": {"entity": {"type": "string"}, "id": {"type": "string"}}, "description": "Entidade de destino", "required": True},
        },
    },
}

PROPOSAL_TOOLS = set(WRITE_TOOLS.keys())


def all_tool_definitions() -> list[dict]:
    """Retorna as definições no formato de function calling do Gemini."""
    defs = []
    for name, spec in {**READ_TOOLS, **WRITE_TOOLS}.items():
        properties = {
            k: {kk: vv for kk, vv in v.items()}
            for k, v in spec["args"].items()
        }
        required = [k for k, v in spec["args"].items() if v.get("required")]
        decl = {
            "name": name,
            "description": spec["description"],
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
        defs.append({"function": decl})
    return defs


def get_tool_definition(name: str) -> dict | None:
    return {**READ_TOOLS, **WRITE_TOOLS}.get(name)


def dispatch_execution(owner, tool_name: str, args: dict) -> dict:
    """Executa uma tool de LEITURA com ownership validado."""
    spec = READ_TOOLS.get(tool_name)
    if spec is None:
        raise ToolNotFoundError(tool_name)
    return spec["handler"](owner, **(args or {}))
