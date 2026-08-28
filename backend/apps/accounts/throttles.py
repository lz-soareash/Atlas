"""Throttles específicos do Atlas.

Além dos throttles globais do REST Framework, definimos limites específicos
para endpoints sensíveis como autenticação (prevenção de força bruta).
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginThrottle(AnonRateThrottle):
    scope = "login"
    rate = "10/min"
