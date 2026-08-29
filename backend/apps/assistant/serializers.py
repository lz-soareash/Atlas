"""Serializers do Atlas Assistant (Fase 6).

- MemorySerializer: CRUD de memórias isoladas por owner.
"""

from rest_framework import serializers

from apps.core.serializers import OwnerModelSerializer

from .models import Memory


class MemorySerializer(OwnerModelSerializer):
    kind_label = serializers.CharField(read_only=True)

    class Meta(OwnerModelSerializer.Meta):
        model = Memory
        fields = [
            "id",
            "kind",
            "kind_label",
            "content",
            "owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "kind_label",
            "owner",
            "created_at",
            "updated_at",
        ]