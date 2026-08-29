"""Providers de IA do Atlas.

- AIProvider: contrato (base.py)
- GeminiProvider: real via SDK oficial (FASE 5)
- DeterministicProvider: fallback offline

`resolve_chat_provider` escolhe automaticamente o melhor disponível.
"""

from .base import AIProvider
from .deterministic import DeterministicProvider
from .gemini import GeminiProvider

__all__ = [
    "AIProvider",
    "GeminiProvider",
    "DeterministicProvider",
    "resolve_chat_provider",
]


def resolve_chat_provider() -> AIProvider:
    """Retorna o Gemini se disponível, senão o fallback determinístico."""
    gemini = GeminiProvider()
    if gemini.available():
        return gemini
    return DeterministicProvider()
