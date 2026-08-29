"""Serializers do Atlas Assistant (Fase 6/7/9).

- MemorySerializer: CRUD de memórias isoladas por owner.
- ToolProposalSerializer: leitura de propostas de escrita (Fase 7).
- AgentRunSerializer: leitura de execuções do agente (Fase 9).
"""

from rest_framework import serializers

from apps.core.serializers import OwnerModelSerializer

from .models import AgentRun, Memory, ToolProposal


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


class ToolProposalSerializer(OwnerModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta(OwnerModelSerializer.Meta):
        model = ToolProposal
        fields = [
            "id",
            "tool",
            "entity",
            "summary",
            "payload",
            "status",
            "status_label",
            "result",
            "owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "tool",
            "entity",
            "summary",
            "payload",
            "status",
            "status_label",
            "result",
            "owner",
            "created_at",
            "updated_at",
        ]


class AgentRunSerializer(OwnerModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta(OwnerModelSerializer.Meta):
        model = AgentRun
        fields = [
            "id",
            "query",
            "status",
            "status_label",
            "iterations",
            "steps",
            "owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields