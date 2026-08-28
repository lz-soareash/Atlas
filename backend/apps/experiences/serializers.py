from rest_framework import serializers

from apps.core.serializers import OwnerModelSerializer
from .models import Experience


class ExperienceSerializer(OwnerModelSerializer):
    kind_label = serializers.CharField(read_only=True)

    class Meta(OwnerModelSerializer.Meta):
        model = Experience
        fields = OwnerModelSerializer.Meta.fields + [
            "kind",
            "kind_label",
            "content",
            "tags",
        ]
