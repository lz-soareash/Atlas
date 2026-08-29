"""Views do app Intelligence (Fase 8).

- InboxViewSet: CRUD de itens do Inbox + action `classify` (IA sugere tipo/
  destino, sem mover nada).
- InteligênciaView: GET /duplicates/, /relationship-suggestions/, /gaps/.
"""

import re

from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.views import OwnerModelViewSet

from .models import InboxItem, InboxStatus
from .serializers import InboxItemSerializer
from .services import detect_duplicates, gap_analysis, productivity_insights, relationship_suggestions


class InboxViewSet(OwnerModelViewSet):
    queryset = InboxItem.objects.all()
    serializer_class = InboxItemSerializer

    @action(detail=True, methods=["post"])
    def classify(self, request, pk=None):
        """Classifica heuristicamente o item (sugestão — nada é movido)."""
        item = self.get_object()
        text = item.content
        low = text.lower()

        if re.search(r"\bcomo\b|\bpor que\b|\bqual\b|\bquando\b|\?$", low):
            item.kind, item.destination = "Pergunta", "Perguntas"
        elif re.search(r"\bquero\b|\bideia\b|\btalvez\b|\bpoderia\b|\bseria\b", low):
            item.kind, item.destination = "Ideia", "Ideias"
        elif re.search(r"\berro\b|\bfalha\b|\baprendi\b|\bdescobri\b|\bsolução\b|\bdeu certo\b", low):
            item.kind, item.destination = "Experiência", "Experiências"
        elif re.search(r"\bdecidi\b|\bdecisão\b|\bescolhi\b", low):
            item.kind, item.destination = "Decisão", "Decisões"
        else:
            item.kind, item.destination = "Conhecimento", "Conhecimentos"
        item.status = InboxStatus.CLASSIFIED
        item.save(update_fields=["kind", "destination", "status", "updated_at"])
        return Response(InboxItemSerializer(item, context={"request": request}).data)


class IntelligenceView(APIView):
    """Endpoint único: /api/intelligence/duplicates|relationship-suggestions|gaps/"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        route = request.path.rstrip("/").split("/")[-1]
        owner = request.user
        if route == "duplicates":
            return Response(detect_duplicates(owner))
        if route == "relationship-suggestions":
            return Response(relationship_suggestions(owner))
        if route == "gaps":
            return Response(gap_analysis(owner))
        if route == "insights":
            return Response(productivity_insights(owner))
        return Response({"detail": "Recurso não encontrado."}, status=404)
