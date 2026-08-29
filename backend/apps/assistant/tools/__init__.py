"""Tools do Atlas Assistant (Fase 7).

A IA NÃO acessa o banco diretamente. Ela só pode usar ferramentas controladas:

- **Leitura** (execução imediata): search_entities, get_entity,
  get_project_context, find_related_entities.
- **Escrita** (exigem CONFIRMAÇÃO do usuário): create_idea, create_question,
  create_knowledge, create_project, create_decision, create_experience,
  create_relationship.

As tools de escrita geram uma `ToolProposal` pendente; a execução real só
acontece quando o usuário aprova via API, sempre validando owner/permissões.
"""

from .registry import (
    PROPOSAL_TOOLS,
    READ_TOOLS,
    WRITE_TOOLS,
    all_tool_definitions,
    dispatch_execution,
    get_tool_definition,
)
from .read import find_related_entities, get_entity, get_project_context, search_entities
from .write import (
    create_decision,
    create_experience,
    create_idea,
    create_knowledge,
    create_project,
    create_question,
    create_relationship,
)

__all__ = [
    "PROPOSAL_TOOLS",
    "READ_TOOLS",
    "WRITE_TOOLS",
    "all_tool_definitions",
    "dispatch_execution",
    "get_tool_definition",
    # leitura
    "search_entities",
    "get_entity",
    "get_project_context",
    "find_related_entities",
    # escrita (via propostas)
    "create_idea",
    "create_question",
    "create_knowledge",
    "create_project",
    "create_decision",
    "create_experience",
    "create_relationship",
]