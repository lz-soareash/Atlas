"""Tools de LEITURA do Atlas Assistant (Fase 7).

Leitura é segura: executada imediatamente pelo serviço, sempre com ownership
validado (nunca expõe dados de outros usuários) e apenas dados ativos.
"""

from __future__ import annotations

from apps.decisions.models import Decision
from apps.experiences.models import Experience
from apps.ideas.models import Idea
from apps.knowledge.models import Knowledge
from apps.projects.models import Project
from apps.questions.models import Question
from apps.relationships.models import Relationship
from apps.search.service import SearchService
from .exceptions import EntityNotFoundError, ToolValidationError

_MODELS = {
    "knowledge": Knowledge,
    "idea": Idea,
    "project": Project,
    "question": Question,
    "decision": Decision,
    "experience": Experience,
}


def search_entities(owner, *, query="", type=None, limit=6):
    """Busca híbrida nas entidades do usuário."""
    limit = max(1, min(int(limit or 6), 20))
    result = SearchService().search(owner, query or "", type=type, limit=limit)
    return {"results": result.get("results", [])}


def _get_or_404(model, owner, obj_id):
    try:
        return model.objects.for_owner(owner).active().get(pk=obj_id)
    except (model.DoesNotExist, ValueError):
        raise EntityNotFoundError()


def _public_entity(entity_key, obj) -> dict:
    base = {
        "entity": entity_key,
        "id": str(obj.pk),
        "title": getattr(obj, "title", None) or getattr(obj, "name", None) or "",
        "summary": getattr(obj, "summary", ""),
        "status": getattr(obj, "status", None),
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat(),
    }
    for field, attr in [
        ("content", "content"),
        ("description", "description"),
        ("objective", "objective"),
        ("decision", "decision"),
        ("rationale", "rationale"),
        ("technologies", "technologies"),
        ("tags", "tags"),
        ("kind", "kind"),
    ]:
        val = getattr(obj, attr, None)
        if val not in (None, ""):
            base[field] = val
    return base


def get_entity(owner, *, entity, id):
    model = _MODELS.get(entity)
    if model is None:
        raise ToolValidationError(detail=f"Entidade inválida: {entity}")
    obj = _get_or_404(model, owner, id)
    return _public_entity(entity, obj)


def get_project_context(owner, *, id):
    project = _get_or_404(Project, owner, id)
    ideas = [i.title for i in project.active_ideas()[:20]]
    return {
        "project": _public_entity("project", project),
        "source_ideas": ideas,
    }


def find_related_entities(owner, *, entity, id):
    origin = _get_or_404(_MODELS.get(entity), owner, id)
    origin_ct = Relationship.eligible_content_types()
    related = []
    for rel in Relationship.objects.for_owner(owner).active().filter(
        origin_id=origin.pk
    ):
        target = rel.target
        if target is None or getattr(target, "is_deleted", False):
            continue
        related.append(
            {
                "type": rel.type,
                "entity": target.__class__.__name__.lower(),
                "id": str(target.pk),
                "title": getattr(target, "title", None) or getattr(target, "name", None) or "",
            }
        )
    return {"related": related}
