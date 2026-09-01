"""Autenticação de integração serviço→serviço via API key (Fase 10).

Usada pelo Jarvis (ou outro cliente externo) nas rotas de integração. A chave
de serviço é criada/retornada apenas uma vez (ver ServiceCredential) e, aqui,
autentica como o usuário (de serviço) associado à credencial — preservando o
isolamento por owner (anti-IDOR) do resto do Atlas.

Uso: header `X-API-Key: <chave>`.
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import ServiceCredential


class ServiceKeyAuthentication(BaseAuthentication):
    """Autentica por X-API-Key → ServiceCredential → User."""

    header = "HTTP_X_API_KEY"
    keyword = "service"

    def authenticate(self, request):
        key = request.META.get(self.header)
        if not key:
            # Sem chave: deixa outros métodos de autenticação decidirem.
            return None

        credential = (
            ServiceCredential.objects.filter(
                key_hash=ServiceCredential._hash(key),
                is_active=True,
                user__is_active=True,
            )
            .select_related("user")
            .first()
        )
        if credential is None:
            raise AuthenticationFailed("Chave de API de serviço inválida ou revogada.")

        credential.last_used_at = timezone.now()
        credential.save(update_fields=["last_used_at", "updated_at"])
        return (credential.user, credential)

    def authenticate_header(self, request):
        return self.keyword
