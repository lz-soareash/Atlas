from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.views import OwnerModelViewSet
from .models import Question
from .serializers import QuestionSerializer


class QuestionViewSet(OwnerModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "question_text", "summary"]
    ordering_fields = ["title", "created_at", "updated_at"]

    @action(detail=True, methods=["post"], url_path="respond")
    def respond(self, request, pk=None):
        """Responde a pergunta criando um Conhecimento a partir dela."""
        question = self.get_object()
        from apps.knowledge.models import Knowledge

        knowledge = Knowledge.objects.create(
            owner=request.user,
            title=request.data.get("title") or question.title,
            content=request.data.get("content", ""),
            summary=request.data.get("summary", ""),
        )
        question.answer(knowledge)
        return Response(
            {"id": str(knowledge.pk), "title": knowledge.title, "question": str(question.pk)},
            status=status.HTTP_201_CREATED,
        )
