"""Dashboard — visão agregada das entidades do usuário (contagens + recentes)."""

from rest_framework import generics, permissions
from rest_framework.response import Response

from apps.decisions.models import Decision
from apps.experiences.models import Experience
from apps.ideas.models import Idea
from apps.knowledge.models import Knowledge
from apps.projects.models import Project
from apps.questions.models import Question

# Entidades em ordem de exibição no dashboard.
ENTITIES = [
    ("conhecimentos", "Conhecimentos", Knowledge, {"route": "/conhecimentos"}),
    ("ideias", "Ideias", Idea, {"route": "/ideias"}),
    ("projetos", "Projetos", Project, {"route": "/projetos"}),
    ("perguntas", "Perguntas", Question, {"route": "/perguntas"}),
    ("decisoes", "Decisões", Decision, {"route": "/decisoes"}),
    ("experiencias", "Experiências", Experience, {"route": "/experiencias"}),
]

RECENT_LIMIT = 5


def _recent_items(owner):
    """Retorna os itens mais recentes (não removidos) agrupados por entidade."""
    result = []
    for key, label, model, meta in ENTITIES:
        queryset = model.objects.for_owner(owner).active().order_by("-updated_at")[:RECENT_LIMIT]

        def build(obj):
            return {
                "entity": key,
                "label": label,
                "title": getattr(obj, "name", None) or obj.title,
                "status": getattr(obj, "status", None),
                "updated_at": obj.updated_at.isoformat(),
                "route": meta["route"],
            }

        result.extend(build(obj) for obj in queryset)

    # Consolida todos os recentes, ordena pelo mais atual e limita a lista final.
    result.sort(key=lambda item: item["updated_at"], reverse=True)
    return result[: (RECENT_LIMIT * len(ENTITIES))]


class DashboardView(generics.GenericAPIView):
    """Retorna contagens e itens recentes do usuário autenticado."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        owner = request.user
        counts = []
        for key, label, model, meta in ENTITIES:
            counts.append(
                {
                    "key": key,
                    "label": label,
                    "count": model.objects.for_owner(owner).active().count(),
                    "route": meta["route"],
                }
            )

        data = {
            "counts": counts,
            "total": sum(c["count"] for c in counts),
            "recent": _recent_items(owner),
        }
        return Response(data)
