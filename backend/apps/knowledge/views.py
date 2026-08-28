from rest_framework import filters, viewsets

from apps.core.views import OwnerModelViewSet
from .models import Knowledge
from .serializers import KnowledgeSerializer


class KnowledgeViewSet(OwnerModelViewSet):
    queryset = Knowledge.objects.all()
    serializer_class = KnowledgeSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "summary", "content", "tags"]
    ordering_fields = ["title", "created_at", "updated_at", "domain_level"]
