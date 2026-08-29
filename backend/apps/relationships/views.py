"""Views do app relationships — CRUD de relacionamentos e geração do grafo."""

from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response

from apps.core.views import OwnerModelViewSet
from .models import Relationship, RelationshipType
from .serializers import RelationshipSerializer

# Emojis/tipos de rota por entidade para o grafo.
ENTITY_META = {
    "knowledge": {"label": "Conhecimento", "emoji": "🧠", "route": "/conhecimentos"},
    "ideas": {"label": "Ideia", "emoji": "💡", "route": "/ideias"},
    "projects": {"label": "Projeto", "emoji": "📁", "route": "/projetos"},
    "questions": {"label": "Pergunta", "emoji": "❓", "route": "/perguntas"},
    "decisions": {"label": "Decisão", "emoji": "⚖️", "route": "/decisoes"},
    "experiences": {"label": "Experiência", "emoji": "📝", "route": "/experiencias"},
}


class RelationshipViewSet(OwnerModelViewSet):
    """CRUD de relacionamentos do usuário (isolado por owner)."""

    queryset = Relationship.objects.all()
    serializer_class = RelationshipSerializer


class GraphView(generics.GenericAPIView):
    """Gera o grafo {nodes, edges} a partir dos relacionamentos do usuário."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        owner = request.user
        relationships = Relationship.objects.for_owner(owner).active()

        nodes = {}
        edges = []

        def add_node(instance):
            if instance is None:
                return
            from django.contrib.contenttypes.models import ContentType

            ct = ContentType.objects.get_for_model(instance)
            key = f"{ct.app_label}:{ct.model}:{instance.pk}"
            is_deleted = getattr(instance, "is_deleted", False)
            if is_deleted:
                return
            meta = ENTITY_META.get(ct.app_label, {})
            nodes[key] = {
                "id": key,
                "key": instance.pk,
                "entity": ct.app_label,
                "label": meta.get("label", ct.model),
                "title": getattr(instance, "name", None) or instance.title,
                "emoji": meta.get("emoji", ""),
                "route": meta.get("route", "#"),
                "status": getattr(instance, "status", None),
            }

        for rel in relationships:
            origin = rel.origin
            target = rel.target
            if origin is None or target is None:
                continue
            if getattr(origin, "is_deleted", False) or getattr(target, "is_deleted", False):
                continue
            add_node(origin)
            add_node(target)

            from django.contrib.contenttypes.models import ContentType

            oc = ContentType.objects.get_for_model(origin)
            tc = ContentType.objects.get_for_model(target)
            edges.append(
                {
                    "id": rel.pk,
                    "source": f"{oc.app_label}:{oc.model}:{origin.pk}",
                    "target": f"{tc.app_label}:{tc.model}:{target.pk}",
                    "type": rel.type,
                    "label": RelationshipType(rel.type).label,
                }
            )

        return Response({"nodes": list(nodes.values()), "edges": edges})
