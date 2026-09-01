"""Views do Cognitive Engine (Fase 10).

- Sessões cognitivas (CRUD + close + query com resposta estruturada).
- Eventos de integração (whitelist extensível).

Todo acesso é isolado por owner (get_queryset filtrando por request.user),
então tanto um humano (JWT) quanto uma conta de serviço (X-API-Key) só
enxergam/tocam a própria sessão (anti-IDOR).
"""

from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.models import AuditLog
from apps.assistant.exceptions import AIError

from .integration import INTEGRATION_EVENT_TYPES
from .models import CognitiveSession, IntegrationEvent
from .serializers import (
    CognitiveSessionQuerySerializer,
    CognitiveSessionSerializer,
    IntegrationEventSerializer,
)
from .services import CognitiveService

_MAX_PROJECT_CONTEXT_KEYS = 25


def _audit(user, action, entity_type, entity_id, summary):
    AuditLog.log(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        summary=summary,
    )


class CognitiveSessionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Sessões cognitivas persistentes do usuário/contas de serviço.

    - GET  /api/cognitive/sessions/
    - POST /api/cognitive/sessions/                      (cria)
    - GET  /api/cognitive/sessions/<id>/
    - POST /api/cognitive/sessions/<id>/query/  (pergunta → resposta estruturada)
    - POST /api/cognitive/sessions/<id>/close/
    """

    serializer_class = CognitiveSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CognitiveSession.objects.for_owner(self.request.user).active()

    def perform_create(self, serializer):
        instance = serializer.save(owner=self.request.user)
        _audit(
            self.request.user,
            "COGNITIVE_SESSION_CREATE",
            "cognitive.CognitiveSession",
            instance.pk,
            f"Criação de sessão cognitiva '{instance.name or '(sem nome)'}'.",
        )

    @action(detail=True, methods=["post"], url_path="query")
    def query(self, request, pk=None):
        """Pergunta a uma sessão; retorna resposta estruturada e persiste o turno."""
        serializer = CognitiveSessionQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = self.get_object()
        if not session.is_active:
            return Response(
                {"detail": "Sessão já encerrada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        query = serializer.validated_data.get("query", "")
        if not query.strip():
            return Response(
                {"detail": "Informe uma consulta (campo 'query')."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = CognitiveService()
        try:
            result = service.reason(
                request.user,
                session,
                query,
                history=service.history(session),
            )
        except AIError as exc:
            return Response(exc.to_public(), status=status.HTTP_502_BAD_GATEWAY)

        service.save_turn(request.user, session, query, result)
        _audit(
            request.user,
            "COGNITIVE_QUERY",
            "cognitive.CognitiveSession",
            session.pk,
            "Pergunta processada pelo motor cognitivo.",
        )
        result["session_id"] = str(session.pk)
        return Response(result)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        session = self.get_object()
        if session.is_active:
            session.close()
            _audit(
                request.user,
                "COGNITIVE_SESSION_CLOSE",
                "cognitive.CognitiveSession",
                session.pk,
                "Encerramento da sessão cognitiva.",
            )
        return Response(CognitiveSessionSerializer(session).data)


class IntegrationEventViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Eventos de integração externa (ex.: Jarvis → Atlas).

    - GET  /api/integration/events/
    - POST /api/integration/events/

    O tipo do evento é validado contra a whitelist extensível; tipos
    desconhecidos são rejeitados (nunca processados implicitamente).
    """

    serializer_class = IntegrationEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return IntegrationEvent.objects.for_owner(self.request.user).active()

    def create(self, request, *args, **kwargs):
        event_type = (request.data.get("type") or "").strip().lower()
        if event_type not in INTEGRATION_EVENT_TYPES:
            return Response(
                {
                    "detail": (
                        "Tipo de evento não aceito. Tipos permitidos: "
                        + ", ".join(sorted(INTEGRATION_EVENT_TYPES))
                        + "."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(request.data.get("payload") or {}) > 100:
            return Response(
                {"detail": "Payload extenso demais."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save(owner=request.user)
        _audit(
            request.user,
            "INTEGRATION_EVENT",
            "cognitive.IntegrationEvent",
            event.pk,
            f"Evento de integração {event.type} recebido.",
        )
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=self.get_success_headers(serializer.data)
        )
