"""Tools de ESCRITA do Atlas Assistant (Fase 7).

Escrita NUNCA é executada diretamente pelo modelo. Cada tool de escrita valida
os argumentos e devolve um payload normalizado que será guardado como uma
`ToolProposal` pendente. A execução real (criação da entidade) só acontece
quando o usuário aprova via `POST /api/assistant/tools/approve/`, sempre com
ownership validado.
"""

from __future__ import annotations

from apps.core.models import Status
from apps.decisions.models import Decision
from apps.experiences.models import Experience
from apps.ideas.models import Idea
from apps.knowledge.models import Knowledge
from apps.projects.models import Project
from apps.questions.models import Question
from apps.relationships.models import Relationship, RelationshipType

from .exceptions import EntityNotFoundError, ToolValidationError

_MODELS = {
    "knowledge": Knowledge,
    "idea": Idea,
    "project": Project,
    "question": Question,
    "decision": Decision,
    "experience": Experience,
}

_KIND_CHOICES = {"error", "solution", "discovery", "experiment", "lesson"}
_REL_TYPES = {t.value for t in RelationshipType}


def _clean_fields(**fields):
    """Remove campos vazios do payload antes de persistir."""
    out = {}
    for k, v in fields.items():
        if v in (None, "", [], {}):
            continue
        out[k] = v
    return out


def create_idea(owner, *, title, description="", summary=""):
    if not title or not str(title).strip():
        raise ToolValidationError(detail="Ideia precisa de título.")
    return {"entity": "idea", "payload": _clean_fields(title=title, description=description, summary=summary)}


def create_question(owner, *, title, question_text=""):
    if not title or not str(title).strip():
        raise ToolValidationError(detail="Pergunta precisa de texto.")
    return {"entity": "question", "payload": _clean_fields(title=title, question_text=question_text)}


def create_knowledge(owner, *, title, content="", summary="", tags=None):
    if not title or not str(title).strip():
        raise ToolValidationError(detail="Conhecimento precisa de título.")
    return {"entity": "knowledge", "payload": _clean_fields(title=title, content=content, summary=summary, tags=tags or [])}


def create_project(owner, *, name, objective="", description="", technologies=None):
    if not name or not str(name).strip():
        raise ToolValidationError(detail="Projeto precisa de nome.")
    return {"entity": "project", "payload": _clean_fields(name=name, objective=objective, description=description, technologies=technologies or [])}


def create_decision(owner, *, title, context="", problem="", decision="", rationale="", alternatives=None):
    if not title or not str(title).strip():
        raise ToolValidationError(detail="Decisão precisa de título.")
    return {"entity": "decision", "payload": _clean_fields(
        title=title, context=context, problem=problem,
        decision=decision, rationale=rationale, alternatives=alternatives or [],
    )}


def create_experience(owner, *, title, content="", kind=None, tags=None):
    if not title or not str(title).strip():
        raise ToolValidationError(detail="Experiência precisa de título.")
    if kind and kind not in _KIND_CHOICES:
        raise ToolValidationError(detail=f"kind inválido: {kind}")
    return {"entity": "experience", "payload": _clean_fields(title=title, content=content, kind=kind, tags=tags or [])}


def create_relationship(owner, *, type, origin, target):
    if type not in _REL_TYPES:
        raise ToolValidationError(detail=f"Tipo de relacionamento inválido: {type}")
    return {
        "entity": "relationship",
        "payload": _clean_fields(type=type, origin=origin, target=target),
    }


# ---------------------------------------------------------------------------
# Execução de uma proposta aprovada (ownership validado).
# ---------------------------------------------------------------------------

def execute_proposal(owner, proposal) -> dict:
    """Cria a entidade a partir de uma ToolProposal aprovada."""
    entity = proposal.entity
    payload = proposal.payload or {}
    if entity == "idea":
        obj = Idea.objects.create(owner=owner, title=payload["title"], description=payload.get("description", ""), summary=payload.get("summary", ""), status=Status.ACTIVE)
        return _created(obj, "idea")
    if entity == "question":
        obj = Question.objects.create(owner=owner, title=payload["title"], question_text=payload.get("question_text", ""), status=Status.ACTIVE)
        return _created(obj, "question")
    if entity == "knowledge":
        obj = Knowledge.objects.create(owner=owner, title=payload["title"], content=payload.get("content", ""), summary=payload.get("summary", ""), tags=payload.get("tags", []), status=Status.ACTIVE)
        return _created(obj, "knowledge")
    if entity == "project":
        obj = Project.objects.create(owner=owner, name=payload["name"], objective=payload.get("objective", ""), description=payload.get("description", ""), technologies=payload.get("technologies", []), status=Status.ACTIVE)
        return _created(obj, "project")
    if entity == "decision":
        obj = Decision.objects.create(owner=owner, title=payload["title"], context=payload.get("context", ""), problem=payload.get("problem", ""), decision=payload.get("decision", ""), rationale=payload.get("rationale", ""), alternatives=payload.get("alternatives", []), status=Status.ACTIVE)
        return _created(obj, "decision")
    if entity == "experience":
        obj = Experience.objects.create(owner=owner, title=payload["title"], content=payload.get("content", ""), kind=payload.get("kind", Experience._meta.get_field("kind").default), tags=payload.get("tags", []), status=Status.ACTIVE)
        return _created(obj, "experience")
    if entity == "relationship":
        rel = _create_relationship(owner, payload)
        return {"entity": "relationship", "id": str(rel.pk), "type": rel.type, "created": True}
    raise ToolValidationError(detail=f"Entidade de escrita não suportada: {entity}")


def _created(obj, entity):
    return {
        "entity": entity,
        "id": str(obj.pk),
        "title": getattr(obj, "title", None) or getattr(obj, "name", None) or "",
        "created": True,
    }


def _resolve_entity(owner, ref):
    entity = (ref or {}).get("entity")
    obj_id = (ref or {}).get("id")
    model = _MODELS.get(entity)
    if model is None or not obj_id:
        raise EntityNotFoundError()
    try:
        return model.objects.for_owner(owner).active().get(pk=obj_id)
    except (model.DoesNotExist, ValueError):
        raise EntityNotFoundError()


def _create_relationship(owner, payload):
    origin_obj = _resolve_entity(owner, payload.get("origin"))
    target_obj = _resolve_entity(owner, payload.get("target"))
    if origin_obj.pk == target_obj.pk and origin_obj.__class__ is target_obj.__class__:
        raise ToolValidationError(detail="Não é permitido self-loop.")
    return Relationship.objects.create(
        owner=owner,
        type=payload["type"],
        origin=origin_obj,
        target=target_obj,
    )
