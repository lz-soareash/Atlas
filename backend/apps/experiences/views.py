from rest_framework import filters

from apps.core.views import OwnerModelViewSet
from .models import Experience
from .serializers import ExperienceSerializer


class ExperienceViewSet(OwnerModelViewSet):
    queryset = Experience.objects.all()
    serializer_class = ExperienceSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content", "tags", "summary"]
    ordering_fields = ["title", "created_at", "updated_at"]
