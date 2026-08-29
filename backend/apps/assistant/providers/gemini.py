"""GeminiProvider — implementação real do AIProvider via SDK oficial.

FASE 5 (GEMINI CORE).

Capacidades:
- generate_text: chat/generation via google.genai (generate_content), com
  system_instruction, controle de tokens, timeout, retry com backoff, e
  tratamento/classificação de erros sem vazar detalhes internos.
- embed_text / embed_texts: delega ao GeminiEmbeddingProvider existente (Fase 4),
  respeitando o contrato do AIProvider.
- Métricas simples (contadores) e logging.

Sempre tenta usar o Gemini; sem chave, `available()` retorna False e a camada
superior deve cair para o DeterministicProvider (modo offline).
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from django.conf import settings

from .base import AIProvider
from ..exceptions import AIError, ProviderUnavailableError, TokenLimitError
from ..retry import retry_with_backoff

logger = logging.getLogger(__name__)

try:
    from google.genai import Client, types

    _HAS_GENAI = True
except ImportError:  # pragma: no cover
    _HAS_GENAI = False

_ROLE_MAP = {"user": "user", "assistant": "model", "model": "model"}


def _to_content(messages: list[dict[str, Any]]) -> tuple[list[Any], str | None]:
    """Converte mensagens [{role, content}] para contents + system_instruction.

    Mensagens de role "tool" (resultado de function_call) são convertidas para
    `function_response` nativo, propagando `tool_call_id` — essencial para o
    protocolo de function calling confiável em chains (Fase 9). Se a
    construção nativa falhar, cai para texto simples (defensivo).
    """
    system_parts = []
    contents = []
    for msg in messages:
        role = _ROLE_MAP.get(msg.get("role", "user"))
        content = msg.get("content", "")
        if msg.get("role") in ("system", "developer"):
            system_parts.append(content)
            continue
        if msg.get("role") == "tool":
            contents.append(_tool_result_content(msg))
            continue
        contents.append(types.Content(role=role, parts=[types.Part(text=content)]))
    system = "\n".join(system_parts) if system_parts else None
    return contents, system


def _tool_result_content(msg: dict[str, Any]) -> Any:
    """Monta um Content de function_response a partir de uma mensagem de tool."""
    try:
        part = types.Part(
            function_response=types.FunctionResponse(
                name=msg.get("name") or "tool",
                id=msg.get("tool_call_id") or msg.get("id"),
                response={"output": msg.get("content", "")},
            )
        )
    except Exception:  # noqa: BLE001
        part = types.Part(text=str(msg.get("content", "")))
    return types.Content(role="user", parts=[part])


class GeminiProvider(AIProvider):
    """Chat + embeddings via Google Gemini."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.model = model or getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash")
        self.max_retries = getattr(settings, "GEMINI_MAX_RETRIES", 3)
        self.timeout = getattr(settings, "GEMINI_TIMEOUT", 45)
        self.max_tokens = getattr(settings, "GEMINI_MAX_TOKENS", 1024)
        # Métricas simples (in-process).
        self.total_calls = 0
        self.error_count = 0

    def available(self) -> bool:
        return bool(self.api_key) and _HAS_GENAI

    def _client(self) -> Any:
        if not _HAS_GENAI:
            raise ProviderUnavailableError(detail="google-genai não instalado")
        try:
            # Timeout global (esta versão do SDK não aceita timeout por chamada).
            return Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=self.timeout),
            )
        except TypeError:  # pragma: no cover
            return Client(api_key=self.api_key)

    def generate_text(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: Iterable[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self.available():
            raise ProviderUnavailableError()

        client = self._client()
        contents, system = _to_content(messages)
        max_tokens = max_tokens or self.max_tokens

        def call():
            config_kwargs: dict[str, Any] = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
            if system:
                config_kwargs["system_instruction"] = system
            if tools:
                declarations = [
                    t.get("function", t) if isinstance(t, dict) and "function" in t else t
                    for t in tools
                ]
                config_kwargs["tools"] = [
                    types.Tool(function_declarations=declarations)
                ]
            config = types.GenerateContentConfig(**config_kwargs)
            return client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

        try:
            self.total_calls += 1
            response = retry_with_backoff(call, max_retries=self.max_retries)
            text = response.text or ""
            return {"content": text, "tool_calls": _extract_tool_calls(response)}
        except AIError:
            self.error_count += 1
            raise
        except Exception as exc:  # noqa: BLE001
            self.error_count += 1
            logger.exception("Gemini generate_text falhou")
            raise _classify_error(exc) from exc

    # --- Embeddings: delega ao GeminiEmbeddingProvider (Fase 4) ---
    def embed_text(self, text: str, **kwargs: Any) -> list[float]:
        return self._embedding_provider().embed_documents([text])[0]

    def embed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        return self._embedding_provider().embed_documents(texts)

    def _embedding_provider(self):
        from apps.search.embeddings import GeminiEmbeddingProvider

        return GeminiEmbeddingProvider(api_key=self.api_key)


def _extract_tool_calls(response: Any) -> list[dict[str, Any]]:
    """Extrai function calls da resposta, se houver."""
    calls = []
    try:
        for part in response.candidates[0].content.parts:
            fn = part.function_call
            if fn is not None:
                args = {k: v for k, v in fn.args.items()}
                call = {"name": fn.name, "args": args}
                if isinstance(getattr(fn, "id", None), str) and fn.id:
                    call["id"] = fn.id
                calls.append(call)
    except (AttributeError, IndexError, TypeError):
        pass
    return calls


def _classify_error(exc: Exception) -> AIError:
    """Converte exceção do SDK em AIError sem vazar detalhes internos."""
    msg = str(exc)
    low = msg.lower()
    if "resource_exhausted" in low or "quota" in low or "429" in msg:
        from ..exceptions import RateLimitExceededError

        return RateLimitExceededError(detail=msg, retryable=True)
    if "length" in low or "token" in low or "too long" in low or "rich" in low:
        return TokenLimitError(detail=msg)
    if "not found" in low or "no longer available" in low or "invalid argument" in low:
        return AIError(detail=msg)
    return AIError(detail=msg)
