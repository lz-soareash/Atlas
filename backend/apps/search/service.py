"""Serviço de busca híbrida (Fase 4).

Busca textual (sempre disponível) combinada com busca semântica quando um
provider de embeddings está disponível (Gemini com chave, ou fallback
determinístico). Resultados normalizados entre as entidades do Knowledge Core,
isolados por owner e com score de relevância.

Estrutura de resposta por item:
    { entity, label, id, title, snippet, score, route, status,
      source: 'textual' | 'semantic' }
"""

from __future__ import annotations

from django.db import models

from apps.decisions.models import Decision
from apps.experiences.models import Experience
from apps.ideas.models import Idea
from apps.knowledge.models import Knowledge
from apps.projects.models import Project
from apps.questions.models import Question

from .embeddings import (
    EmbeddingError,
    cosine_similarity,
    resolve_embedding_provider,
)

# Entidades indexáveis. weight_title pondera o título vs corpo na relevância.
SEARCH_ENTITIES = [
    {
        "key": "knowledge",
        "label": "Conhecimento",
        "model": Knowledge,
        "route": "/conhecimentos",
        "weight_title": 3.0,
        "fields": ["title", "summary", "content", "tags"],
        "title_field": "title",
    },
    {
        "key": "idea",
        "label": "Ideia",
        "model": Idea,
        "route": "/ideias",
        "weight_title": 3.0,
        "fields": ["title", "summary", "description"],
        "title_field": "title",
    },
    {
        "key": "project",
        "label": "Projeto",
        "model": Project,
        "route": "/projetos",
        "weight_title": 4.0,
        "fields": ["title", "name", "description", "objective", "technologies"],
        "title_field": "name",
    },
    {
        "key": "question",
        "label": "Pergunta",
        "model": Question,
        "route": "/perguntas",
        "weight_title": 3.0,
        "fields": ["title", "question_text"],
        "title_field": "title",
    },
    {
        "key": "decision",
        "label": "Decisão",
        "model": Decision,
        "route": "/decisoes",
        "weight_title": 3.0,
        "fields": ["title", "context", "problem", "decision", "rationale", "alternatives"],
        "title_field": "title",
    },
    {
        "key": "experience",
        "label": "Experiência",
        "model": Experience,
        "route": "/experiencias",
        "weight_title": 3.0,
        "fields": ["title", "content", "tags"],
        "title_field": "title",
    },
]


def _display_title(obj, title_field):
    val = getattr(obj, title_field, None) or getattr(obj, "title", None) or ""
    return str(val) or getattr(obj, "name", None) or str(obj)


def _match_score(obj, tokens, meta):
    """Pontuação textual de relevância do objeto para os termos buscados."""
    title_field = meta["title_field"]
    title = (getattr(obj, title_field, None) or getattr(obj, "title", "") or "")
    title = str(title).lower()
    body = " ".join(
        str(getattr(obj, f, "") or "") for f in meta["fields"]
    ).lower()
    score = 0.0
    for token in tokens:
        t_in_title = token in title
        t_in_body = token in body
        # prefix no título vale mais que substring no corpo.
        if title.startswith(token):
            score += meta["weight_title"] * 2.0
        elif t_in_title:
            score += meta["weight_title"]
        elif t_in_body:
            score += 1.0
        else:
            return 0.0  # todo termo deve aparecer em alguma parte
    return score


def _snippet(obj, tokens, meta):
    """Trecho textual em torno da primeira ocorrência de um termo."""
    text = " ".join(
        str(getattr(obj, f, "") or "") for f in meta["fields"]
    )
    text = text or "".join(
        str(getattr(obj, f, "") or "") for f in meta["fields"]
    )
    for token in tokens:
        idx = text.lower().find(token)
        if idx >= 0:
            start = max(0, idx - 40)
            end = min(len(text), idx + len(token) + 80)
            prefix = "…" if start > 0 else ""
            suffix = "…" if end < len(text) else ""
            return f"{prefix}{text[start:end].strip()}{suffix}"
    return (text[:120] + "…") if len(text) > 120 else text


def _semantic(provider, query, items):
    """Enriquece itens com similaridade semântica quando possível.

    Gera o embedding da query e, em lote, dos documentos candidatos,
    combinando a pontuação textual com a similaridade de cosseno.
    """
    texts = [f"{it['title']} {it['hidden_text']}".strip() for it in items]
    try:
        query_vec = provider.embed_documents([query])[0]
        doc_vecs = provider.embed_documents(texts)
    except (EmbeddingError, IndexError):
        return None
    for it, vec in zip(items, doc_vecs):
        it["sem_score"] = cosine_similarity(query_vec, vec)
    return query_vec


class SearchService:
    """Busca normalizada sobre as entidades do usuário."""

    def search(self, owner, q="", *, type=None, limit=20, semantic=True):
        q = (q or "").strip()
        items = []

        for meta in SEARCH_ENTITIES:
            if type and type != meta["key"]:
                continue
            tokens = [t.lower() for t in q.split()] if q else []
            queryset = meta["model"].objects.for_owner(owner).active()
            if not tokens:
                # Sem termos: lista recente pontuada pela atualização.
                for obj in queryset[:limit]:
                    items.append(self._base_item(obj, meta, score=0.0, tokens=())[0])
                continue
            for obj in queryset:
                score = _match_score(obj, tokens, meta)
                if score > 0:
                    item, text = self._base_item(obj, meta, score, tokens)
                    item["hidden_text"] = text
                    items.append(item)

        items.sort(key=lambda it: it["score"], reverse=True)
        items = items[:limit]

        # Combinar com semântica sempre que um provider estiver disponível.
        semantic_used = False
        if semantic and q and items:
            provider = resolve_embedding_provider()
            if provider is not None:
                try:
                    _semantic(provider, q, items)
                    for it in items:
                        s = it.get("sem_score")
                        if s is not None:
                            it["score"] = it["score"] + s * 5.0
                            it["source"] = "semantic"
                            semantic_used = True
                except (EmbeddingError, IndexError):
                    semantic_used = False

        items.sort(key=lambda it: it["score"], reverse=True)
        for it in items:
            it.pop("hidden_text", None)
        return {
            "query": q,
            "semantic_available": semantic_used,
            "results": items,
        }

    def _base_item(self, obj, meta, score, tokens):
        title = _display_title(obj, meta["title_field"])
        snippet = _snippet(obj, tokens, meta) if tokens else self._default_snippet(obj, meta)
        text = " ".join(
            str(getattr(obj, f, "") or "") for f in meta["fields"]
        )
        return (
            {
                "id": str(obj.pk),
                "entity": meta["key"],
                "label": meta["label"],
                "title": title,
                "snippet": snippet[:200],
                "score": round(score, 4),
                "route": meta["route"],
                "status": getattr(obj, "status", None),
                "source": "textual",
            },
            text,
        )

    def _default_snippet(self, obj, meta):
        for f in meta["fields"]:
            val = getattr(obj, f, "") or ""
            if val:
                return str(val)
        return ""
