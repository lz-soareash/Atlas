from rest_framework import serializers

from apps.core.serializers import OwnerModelSerializer
from .models import Decision


class DecisionSerializer(OwnerModelSerializer):
    class Meta(OwnerModelSerializer.Meta):
        model = Decision
        fields = OwnerModelSerializer.Meta.fields + [
            "context",
            "problem",
            "alternatives",
            "decision",
            "rationale",
            "consequences",
            "decided_at",
        ]
