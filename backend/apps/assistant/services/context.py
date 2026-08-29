"""Build de contexto (retrieval) para o chat do Atlas.

Recupera contexto relevante do usuário a partir da busca híbrida da Fase 4
e do grafo de relacionamentos (Fase 3). Nunca envia o banco inteiro —
apenas o contexto relevante e rastreável.
"""

from __future__ import annotations

from django.conf import settings

from apps.assistant.models import Memory
from apps.relationships.models import Relationship
from apps.search.service import SearchService

MAX_RESULTS = 6


def build_context(owner, query: str, *, include_graph: bool = True) -> dict:
    """Monta o contexto do usuário para uma pergunta.

    Combina:
    - busca híbrida (Fase 4) → fontes rastreáveis;
    - arestas do grafo (Fase 3);
    - memórias explícitas do usuário (Fase 6).
    """
    limit = getattr(settings, "MAX_RETRIEVAL_RESULTS", MAX_RESULTS)

    search = SearchService().search(owner, query, limit=limit)
    sources = search.get("results", [])

    graph_edges = []
    if include_graph:
        graph_edges = _graph_edges(owner, limit=4)

    return {
        "query": query,
        "sources": sources,
        "graph_edges": graph_edges,
        "memories": _memories(owner),
        "semantic_available": search.get("semantic_available", False),
    }


def _memories(owner, limit: int | None = None) -> list[dict]:
    """Memórias ativas do usuário (mais recentes primeiro)."""
    limit = limit or getattr(settings, "MAX_MEMORIES", 20)
    qs = Memory.objects.for_owner(owner).active()[:limit]
    return [
        {"label": m.get_kind_display(), "content": m.content}
        for m in qs.iterator()
    ]


def _graph_edges(owner, limit: int = 4) -> list[dict]:
    """Arestas do grafo do usuário (para dar contexto de conexões)."""
    edges = []
    for rel in Relationship.objects.for_owner(owner).active()[:limit]:
        edges.append(
            {
                "type": rel.type,
                "origin": _endpoint_summary(rel.origin),
                "target": _endpoint_summary(rel.target),
            }
        )
    return edges


def _endpoint_summary(obj) -> str:
    if obj is None:
        return "?"
    title = getattr(obj, "title", None) or getattr(obj, "name", None) or ""
    return f"{obj.__class__.__name__}:{' ' + str(title) if title else ''}"
