"""Serializers base reutilizados pelas entidades do Knowledge Core."""

from rest_framework import serializers


class OwnerModelSerializer(serializers.ModelSerializer):
    """Serializer que expõe `owner` e `created_at`/`updated_at` como somente
    leitura e mantém `deleted_at` oculto (soft delete gerenciado pela view)."""

    owner = serializers.UUIDField(read_only=True, source="owner_id")

    class Meta:
        fields = [
            "id",
            "title",
            "summary",
            "status",
            "owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "owner",
            "created_at",
            "updated_at",
        ]
