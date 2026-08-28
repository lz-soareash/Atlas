from rest_framework import serializers

from apps.core.serializers import OwnerModelSerializer
from .models import Project


class ProjectSerializer(OwnerModelSerializer):
    name = serializers.CharField(max_length=255)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)

    class Meta(OwnerModelSerializer.Meta):
        model = Project
        fields = OwnerModelSerializer.Meta.fields + [
            "name",
            "description",
            "objective",
            "technologies",
        ]
