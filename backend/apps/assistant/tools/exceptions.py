"""Exceções específicas das tools do Atlas Assistant."""

from apps.assistant.exceptions import AIError


class ToolError(AIError):
    """Erro genérico ao executar uma tool."""

    code = "tool_error"
    user_message = "Não foi possível executar a ferramenta."


class ToolNotFoundError(ToolError):
    """Tool não existe ou não é executável."""

    code = "tool_not_found"

    def __init__(self, name: str, **kwargs):
        super().__init__(detail=f"Tool desconhecida: {name}", **kwargs)


class ToolValidationError(ToolError):
    """Argumentos inválidos para a tool."""

    code = "tool_validation"


class EntityNotFoundError(ToolError):
    """Entidade não encontrada (ou não pertence ao usuário)."""

    code = "entity_not_found"
    user_message = "Entidade não encontrada."


class ProposalNotExecutableError(ToolError):
    """Proposta não pode ser executada (já usada/cancelada/expirada)."""

    code = "proposal_not_executable"
    user_message = "Esta proposta de escrita não pode ser executada (já resolvida)."
