from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.views import OwnerModelViewSet
from .models import Idea
from .serializers import ConvertIdeaSerializer, IdeaSerializer


class IdeaViewSet(OwnerModelViewSet):
    queryset = Idea.objects.all()
    serializer_class = IdeaSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "summary"]
    ordering_fields = ["title", "created_at", "updated_at"]

    @action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request, pk=None):
        """Transforma a Ideia em um Projeto (registrando a origem)."""
        idea = self.get_object()
        serializer = ConvertIdeaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = idea.convert_to_project(**serializer.validated_data)
        return Response(
            {"id": str(project.pk), "name": project.name, "idea": str(idea.pk)},
            status=status.HTTP_201_CREATED,
        )
