"""Views do Atlas Assistant (Fase 5/6/7)."""

from rest_framework import permissions, serializers, status
from rest_framework.decorators import action
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

from .models import Memory, ProposalStatus, ToolProposal
from .serializers import MemorySerializer, ToolProposalSerializer


class MemoryViewSet(OwnerModelViewSet):
    """CRUD de memórias do usuário (isolamento por owner + soft delete)."""

    queryset = Memory.objects.all()
    serializer_class = MemorySerializer


class ToolProposalViewSet(OwnerModelViewSet):
    """Leitura/gestão de propostas de escrita da IA (isolamento por owner)."""

    queryset = ToolProposal.objects.all()
    serializer_class = ToolProposalSerializer
    # Sem create via API (propostas nascem no ChatService); apenas as ações.
    http_method_names = ["get", "patch", "delete", "post"]

    def get_queryset(self):
        return super().get_queryset().filter(status=ProposalStatus.PENDING)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        """Executa a proposta aprovada (cria a entidade no Atlas)."""
        proposal = self.get_object()
        if proposal.status != ProposalStatus.PENDING:
            return Response(
                {"detail": "Proposta já resolvida."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            from apps.assistant.tools.write import execute_proposal

            result = execute_proposal(request.user, proposal)
        except AIError as exc:
            return Response({"detail": exc.user_message}, status=status.HTTP_400_BAD_REQUEST)

        proposal.status = ProposalStatus.APPROVED
        proposal.result = result
        proposal.save(update_fields=["status", "result", "updated_at"])
        return Response(
            {"proposal": str(proposal.pk), "result": result},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        """Rejeita a proposta (não cria nada)."""
        proposal = self.get_object()
        if proposal.status != ProposalStatus.PENDING:
            return Response(
                {"detail": "Proposta já resolvida."},
                status=status.HTTP_409_CONFLICT,
            )
        proposal.status = ProposalStatus.REJECTED
        proposal.save(update_fields=["status", "updated_at"])
        return Response({"proposal": str(proposal.pk), "status": proposal.status})


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
