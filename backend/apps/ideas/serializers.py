from rest_framework import serializers

from apps.core.serializers import OwnerModelSerializer
from .models import Idea


class IdeaSerializer(OwnerModelSerializer):
    class Meta(OwnerModelSerializer.Meta):
        model = Idea
        fields = OwnerModelSerializer.Meta.fields + [
            "description",
            "converted",
            "project",
        ]
        read_only_fields = OwnerModelSerializer.Meta.read_only_fields + ["converted", "project"]


class ConvertIdeaSerializer(serializers.Serializer):
    """Payload para transformar uma Ideia em Projeto."""

    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    objective = serializers.CharField(required=False, allow_blank=True)
    technologies = serializers.ListField(child=serializers.CharField(), required=False)
