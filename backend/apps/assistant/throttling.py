"""Throttling da camada de IA.

Limite de requisições de chat por usuário para controlar custo/abuso,
além do throttle global já aplicado pelo DRF.
"""

from rest_framework.throttling import SimpleRateThrottle


class GeminiRateThrottle(SimpleRateThrottle):
    """Limita chamadas de chat do Gemini por usuário (scope 'gemini')."""

    scope = "gemini"

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None  # apenas usuários autenticados
        return self.cache_format % {"scope": self.scope, "ident": user.pk}
