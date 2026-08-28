from rest_framework import filters

from apps.core.views import OwnerModelViewSet
from .models import Decision
from .serializers import DecisionSerializer


class DecisionViewSet(OwnerModelViewSet):
    queryset = Decision.objects.all()
    serializer_class = DecisionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "context", "problem", "decision", "rationale"]
    ordering_fields = ["title", "decided_at", "created_at", "updated_at"]
