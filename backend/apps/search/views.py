"""Views da busca híbrida (Fase 4)."""

from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .service import SEARCH_ENTITIES, SearchService

# Aceita chaves canônicas e aliases em português, mapeando para a chave do modelo.
VALID_TYPES = {m["key"]: m["key"] for m in SEARCH_ENTITIES}
VALID_TYPES.update(
    {
        "conhecimentos": "knowledge",
        "conhecimento": "knowledge",
        "ideias": "idea",
        "ideia": "idea",
        "projetos": "project",
        "projeto": "project",
        "perguntas": "question",
        "pergunta": "question",
        "decisoes": "decision",
        "decisão": "decision",
        "decisao": "decision",
        "experiencias": "experience",
        "experiência": "experience",
        "experiencia": "experience",
    }
)


class SearchView(APIView):
    """GET /api/search/?q=...&type=...&limit=...

    Busca híbrida (textual + semântica) sobre todas as entidades do usuário.
    Resultados normalizados e isolados por owner.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        q = request.query_params.get("q", "").strip()
        type_ = request.query_params.get("type", "").strip().lower()
        limit_raw = request.query_params.get("limit", "20").strip()

        if type_ and type_ not in VALID_TYPES:
            raise serializers.ValidationError({"type": "Tipo de entidade inválido."})
        mapped = VALID_TYPES.get(type_, type_)

        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 100))

        if not q:
            return Response({"query": "", "semantic_available": False, "results": []})

        data = SearchService().search(request.user, q, type=mapped or None, limit=limit)
        return Response(data)
