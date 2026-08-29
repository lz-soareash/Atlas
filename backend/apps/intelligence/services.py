"""Intelligence — análise de conhecimento do usuário (Fase 8).

Heurísticas determinísticas (sem LLM) que retornam SUGESTÕES, nunca ações
automáticas:
- duplicates: candidatos a duplicata entre (e dentro de) entidades.
- relationship_suggestions: pares que podem merecer um relacionamento.
- gaps: tópicos que aparecem em perguntas/projetos mas sem conhecimento solto.

Tudo isolado por owner e apenas dados ativos.
"""

from __future__ import annotations

import re
from collections import Counter

from apps.decisions.models import Decision
from apps.experiences.models import Experience
from apps.ideas.models import Idea
from apps.knowledge.models import Knowledge
from apps.projects.models import Project
from apps.questions.models import Question
from apps.search.embeddings import cosine_similarity, resolve_embedding_provider

_ENTITIES = [
    ("knowledge", "Conhecimento", Knowledge, "title", "/conhecimentos", ["title", "summary", "content", "tags"]),
    ("idea", "Ideia", Idea, "title", "/ideias", ["title", "summary", "description"]),
    ("project", "Projeto", Project, "name", "/projetos", ["name", "objective", "description", "technologies"]),
    ("question", "Pergunta", Question, "title", "/perguntas", ["title", "question_text"]),
    ("decision", "Decisão", Decision, "title", "/decisoes", ["title", "context", "problem", "decision", "rationale", "alternatives"]),
    ("experience", "Experiência", Experience, "title", "/experiencias", ["title", "content", "tags"]),
]


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[\wÀ-ÿ]+", (text or "").lower())
    stop = {"de", "da", "do", "das", "dos", "a", "o", "as", "os", "e", "em",
            "para", "com", "por", "na", "no", "nas", "nos", "que", "um", "uma",
            "é", "como", "ter", "se", "sobre", "the", "and", "to", "of", "a"}
    return {w for w in words if w not in stop and len(w) > 2}


def _load_items(owner):
    items = []
    for key, label, model, title_field, route, fields in _ENTITIES:
        for obj in model.objects.for_owner(owner).active():
            items.append(
                {
                    "entity": key,
                    "label": label,
                    "id": str(obj.pk),
                    "title": getattr(obj, "name", None) or obj.title,
                    "route": route,
                    "text": (
                        (getattr(obj, "name", None) or obj.title)
                        + " "
                        + " ".join(str(getattr(obj, f, "") or "") for f in fields)
                    ),
                }
            )
    return items


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def detect_duplicates(owner, *, threshold: float = 0.55, limit: int = 20):
    """Candidatos a duplicata por similaridade de tokens + semântica."""
    items = _load_items(owner)
    tokens = [(_tokenize(it["text"]), it) for it in items]
    groups = []

    embedding = resolve_embedding_provider()
    sem_fallback = embedding is not None
    vectors = None
    if embedding is not None:
        try:
            vectors = {
                it["id"]: embedding.embed_documents([it["text"]])[0]
                for it in items
            }
        except Exception:  # noqa: BLE001
            vectors = None
            sem_fallback = False

    for i in range(len(items)):
        ti, ita = tokens[i]
        for j in range(i + 1, len(items)):
            tj, itb = tokens[j]
            if ita["entity"] != itb["entity"]:
                continue  # apenas mesma entidade por ora
            sim = _jaccard(ti, tj)
            sem = 0.0
            if vectors and ita["id"] in vectors and itb["id"] in vectors:
                sem = cosine_similarity(vectors[ita["id"]], vectors[itb["id"]])
                sim = max(sim, sem)
            if sim >= threshold or (sem and sem >= 0.85):
                groups.append(
                    {
                        "a": _public(ita),
                        "b": _public(itb),
                        "similarity": round(sim, 3),
                        "semantic_score": round(sem, 3),
                    }
                )

    groups.sort(key=lambda g: g["similarity"], reverse=True)
    return {
        "semantic_available": sem_fallback,
        "count": len(groups[:limit]),
        "groups": groups[:limit],
    }


def _public(it):
    return {
        "entity": it["entity"],
        "label": it["label"],
        "id": it["id"],
        "title": it["title"],
        "route": it["route"],
    }


def relationship_suggestions(owner, *, threshold: float = 0.4, limit: int = 20):
    """Sugere pares de entidades que compartilham vocabulário (candidato a
    link no grafo). Não cria nada — apenas sugere."""
    items = _load_items(owner)
    tokens = [(id(it), _tokenize(it["text"]), it) for it in items]
    suggestions = []

    for k, (_, ti, ita) in enumerate(tokens):
        for _, tj, itb in tokens[k + 1:]:
            if ita["entity"] == itb["entity"]:
                continue
            sim = _jaccard(ti, tj)
            if sim >= threshold:
                suggestions.append(
                    {
                        "origin": _public(ita),
                        "target": _public(itb),
                        "similarity": round(sim, 3),
                        "suggested": "RELACIONADO_A",
                    }
                )
    suggestions.sort(key=lambda s: s["similarity"], reverse=True)
    return {"count": len(suggestions[:limit]), "suggestions": suggestions[:limit]}


def gap_analysis(owner, *, limit: int = 20):
    """Tópicos frequentes em perguntas/projetos/ideias que ainda não têm um
    Conhecimento dedicado (indicando lacuna de aprendizado)."""
    topic_counter: Counter = Counter()

    def harvest(model, fields):
        for obj in model.objects.for_owner(owner).active():
            tokens = _tokenize(" ".join(str(getattr(obj, f, "") or "") for f in fields))
            topic_counter.update(tokens)

    harvest(Question, ["title", "question_text"])
    harvest(Project, ["name", "objective", "description"])
    harvest(Idea, ["title", "description"])

    known = set()
    for obj in Knowledge.objects.for_owner(owner).active():
        known.update(_tokenize(obj.title))
        known.update(_tokenize(obj.summary))

    gaps = []
    for word, count in topic_counter.most_common(limit * 3):
        if word in known:
            continue
        if count >= 2:
            gaps.append({"topic": word, "mentions": count, "suggested": f"Conhecimento: {word}"})
        if len(gaps) >= limit:
            break
    return {"count": len(gaps), "gaps": gaps}
