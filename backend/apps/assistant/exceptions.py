"""Exceções da camada de IA.

Padronizam o tratamento de erros entre provider, services e API, garantindo que
a resposta ao usuário nunca exponha detalhes internos (chave, stack, SDK).
"""

from __future__ import annotations


class AIError(Exception):
    """Erro genérico da camada de IA."""

    code = "ai_error"
    user_message = "Erro inesperado ao processar a solicitação com a IA."

    def __init__(self, *, detail: str = "", retryable: bool = False):
        super().__init__(detail or self.user_message)
        self.detail = detail
        self.retryable = retryable

    def to_public(self) -> dict:
        return {"code": self.code, "message": self.user_message, "retryable": self.retryable}


class ProviderUnavailableError(AIError):
    """Nenhum provedor de IA disponível (ex.: sem chave)."""

    code = "provider_unavailable"
    user_message = "Nenhum provedor de IA configurado. Configure GEMINI_API_KEY."


class RateLimitExceededError(AIError):
    """Limite de requisições por usuário atingido."""

    code = "rate_limited"
    user_message = "Limite de requisições atingido. Tente novamente em instantes."


class TokenLimitError(AIError):
    """Limite de tokens do modelo excedido no pedido."""

    code = "token_limit"
    user_message = "Solicitação muito longa. Reduza o contexto e tente novamente."


class MaxRetriesExceededError(AIError):
    """Falha persistente após todas as tentativas de retry."""

    code = "max_retries"
    user_message = "O serviço de IA está temporariamente indisponível. Tente novamente."
