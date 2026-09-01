"""Serializers do Cognitive Engine (Fase 10)."""

from rest_framework import serializers

from .models import CognitiveSession, IntegrationEvent, SessionMessage


class SessionMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionMessage
        fields = ["id", "role", "content", "sources", "created_at"]


class CognitiveSessionSerializer(serializers.ModelSerializer):
    messages = SessionMessageSerializer(many=True, read_only=True)

    class Meta:
        model = CognitiveSession
        fields = [
            "id",
            "name",
            "project_context",
            "metadata",
            "is_active",
            "closed_at",
            "messages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "closed_at", "created_at", "updated_at"]


class CognitiveSessionQuerySerializer(serializers.Serializer):
    query = serializers.CharField(required=False, allow_blank=True, default="")
    session_id = serializers.UUIDField(required=False, allow_null=True)


class IntegrationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationEvent
        fields = [
            "id",
            "type",
            "payload",
            "processed",
            "error",
            "created_at",
        ]
        read_only_fields = ["id", "processed", "error", "created_at"]
