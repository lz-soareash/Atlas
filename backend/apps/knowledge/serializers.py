from rest_framework import serializers

from apps.core.serializers import OwnerModelSerializer
from .models import DomainLevel, Knowledge


class KnowledgeSerializer(OwnerModelSerializer):
    domain_level_label = serializers.CharField(read_only=True)

    class Meta(OwnerModelSerializer.Meta):
        model = Knowledge
        fields = OwnerModelSerializer.Meta.fields + [
            "content",
            "domain_level",
            "domain_level_label",
            "tags",
        ]
