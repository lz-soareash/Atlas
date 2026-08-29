"""Serializers do app Intelligence (Fase 8)."""

from rest_framework import serializers

from apps.core.serializers import OwnerModelSerializer

from .models import InboxItem


class InboxItemSerializer(OwnerModelSerializer):
    class Meta(OwnerModelSerializer.Meta):
        model = InboxItem
        fields = [
            "id",
            "content",
            "status",
            "kind",
            "destination",
            "summary",
            "owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "kind",
            "destination",
            "summary",
            "owner",
            "created_at",
            "updated_at",
        ]
