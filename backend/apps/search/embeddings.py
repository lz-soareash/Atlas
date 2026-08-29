"""Provedores de embeddings (Fase 4 — SEARCH + EMBEDDINGS).

Contrato no estilo do AIProvider (Fase 1): a camada de busca depende apenas
desta interface, nunca de um SDK específico.

- EmbeddingProvider       : contrato abstrato
- FingerprintEmbeddingProvider : fallback determinístico (funciona sem API,
                                 para dev/testes e modo offline)
- GeminiEmbeddingProvider : embeddings reais via API Google (google.genai),
                            disponível quando GEMINI_API_KEY está configurada

A lógica de busca (SearchService) deve sempre tentar o Gemini quando
disponível e cair para o fallback determinístico / textual caso contrário.
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import Iterable

from django.conf import settings

_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


class EmbeddingError(Exception):
    """Erro ao gerar embeddings (ex.: API indisponível, sem chave)."""


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _WORD_RE.findall(text or "")]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similaridade de cosseno entre dois vetores de mesma dimensão."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class EmbeddingProvider(ABC):
    """Contrato de um provedor de embeddings.

    `available()` indica se o provider pode ser usado agora (ex.: chave
    configurada). `embed_documents` gera vetores em lote (otimizável por SDK).
    """

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        """Retorna um vetor por texto, na mesma ordem."""


class FingerprintEmbeddingProvider(EmbeddingProvider):
    """Fallback determinístico: vetor por hashing de features (hashing trick).

    Não depende de API externa (funciona offline, em testes e em SQLite).
    Vetores são determinísticos: o mesmo texto produz sempre o mesmo vetor,
    permitindo buscar por similaridade de cosseno no espaço de tokens.
    """

    dim = settings.EMBEDDING_DIM

    def available(self) -> bool:
        return True

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        return vec

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embeddings reais via API Gemini (google.genai).

    Requer `GEMINI_API_KEY`. Retorna vetores normalizados da dimensão do
    modelo configurado em `EMBEDDING_MODEL`.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.model = model or getattr(settings, "EMBEDDING_MODEL", "gemini-embedding-001")

    def available(self) -> bool:
        return bool(self.api_key)

    def _client(self):
        try:
            from google.genai import Client, types
        except ImportError as exc:  # pragma: no cover
            raise EmbeddingError("google-genai não instalado") from exc
        self._types = types
        return Client(api_key=self.api_key)

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        if not self.available():
            raise EmbeddingError("GEMINI_API_KEY não configurada.")
        items = list(texts)
        if not items:
            return []
        client = self._client()
        kwargs = {"model": self.model, "contents": items}
        if hasattr(self._types, "EmbedContentConfig"):
            # Conteúdo de busca/retrieval para melhor alinhamento semântico.
            try:
                kwargs["config"] = self._types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT"
                )
            except Exception:  # pragma: no cover
                kwargs.pop("config", None)
        try:
            result = client.models.embed_content(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingError(str(exc)) from exc
        return [
            list(e.values) for e in result.embeddings if getattr(e, "values", None)
        ]


def resolve_embedding_provider() -> EmbeddingProvider:
    """Retorna o melhor provedor disponível (Gemini se houver chave)."""
    gemini = GeminiEmbeddingProvider()
    if gemini.available():
        return gemini
    return FingerprintEmbeddingProvider()
