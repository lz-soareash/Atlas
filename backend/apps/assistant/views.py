"""Views do Atlas Assistant (Fase 5 — Gemini Core; Fase 6 — Memória)."""

from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assistant.exceptions import (
    AIError,
    RateLimitExceededError,
    TokenLimitError,
)
from apps.assistant.services import ChatService
from apps.assistant.throttling import GeminiRateThrottle
from apps.core.views import OwnerModelViewSet

from .models import Memory
from .serializers import MemorySerializer


class MemoryViewSet(OwnerModelViewSet):
    """CRUD de memórias do usuário (isolamento por owner + soft delete)."""

    queryset = Memory.objects.all()
    serializer_class = MemorySerializer


class ChatView(APIView):
    """POST /api/assistant/chat/ — chat com contexto do Atlas.

    Corpo: { "messages": [ {"role": "user"|"assistant", "content": "..."} ] }
    Retorna: { answer, sources, provider, classification, semantic_available }
    """

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [GeminiRateThrottle]

    def post(self, request, *args, **kwargs):
        messages = self._validate_messages(request.data)
        try:
            data = ChatService().chat(request.user, messages)
        except RateLimitExceededError as exc:
            return Response({"detail": exc.user_message}, status=429)
        except TokenLimitError as exc:
            return Response({"detail": exc.user_message}, status=400)
        except AIError as exc:
            return Response({"detail": exc.user_message}, status=502)
        return Response(data)

    def _validate_messages(self, payload) -> list:
        messages = payload.get("messages", []) if isinstance(payload, dict) else []
        if not isinstance(messages, list) or not messages:
            raise serializers.ValidationError({"messages": "Histórico de mensagens é obrigatório."})
        return messages
