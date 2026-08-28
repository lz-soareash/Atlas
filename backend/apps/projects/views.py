from rest_framework import filters

from apps.core.views import OwnerModelViewSet
from .models import Project
from .serializers import ProjectSerializer


class ProjectViewSet(OwnerModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "objective", "technologies"]
    ordering_fields = ["name", "created_at", "updated_at"]
