"""Retry com backoff exponencial e jitter para chamadas de IA."""

from __future__ import annotations

import logging
import random
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Códigos/erros considerados transientes e passíveis de retry.
_TRANSIENT = ("429", "500", "502", "503", "504")
# Timeouts de conexão/leitura são transitórios (rede instável/proxy, etc.).
_TIMEOUT_MARKERS = (
    "timeout",
    "timed out",
    "connecttimeout",
    "readtimeout",
    "connection reset",
    "connection refused",
)


def _is_retryable(exc: BaseException) -> bool:
    """Decide se uma exceção merece nova tentativa."""
    msg = str(exc).lower()
    if any(code in msg for code in _TRANSIENT):
        return True
    if any(marker in msg for marker in _TIMEOUT_MARKERS):
        return True
    return False


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_retries: int,
    base_delay: float = 1.0,
    max_delay: float = 12.0,
) -> T:
    """Executa `fn` com tentativas em backoff exponencial + jitter.

    Só re-tenta erros transientes (429/5xx). Após esgotar as tentativas,
    propaga a última exceção como `MaxRetriesExceededError`.
    """
    from .exceptions import MaxRetriesExceededError

    attempt = 0
    while True:
        try:
            return fn()
        except BaseException as exc:  # noqa: BLE001
            attempts_left = max_retries - attempt
            if attempts_left <= 0 or not _is_retryable(exc):
                raise
            attempt += 1
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            delay = delay * (0.5 + random.random() / 2)  # jitter
            logger.warning("Retry %d/%d em %.2fs: %s", attempt, max_retries, delay, exc)
            time.sleep(delay)
    raise MaxRetriesExceededError()
