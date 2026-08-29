"""Serializers do app relationships."""

from django.apps import apps as django_apps
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from .models import Relationship, RelationshipType


class EndpointField(serializers.Field):
    """Representa um GenericForeignKey como {model, id} (ex.: knowledge.knowledge)."""

    def to_representation(self, obj):
        ct = ContentType.objects.get_for_model(obj)
        return {"model": f"{ct.app_label}.{ct.model}", "id": str(obj.pk)}

    def to_internal_value(self, data):
        if not isinstance(data, dict) or "model" not in data or "id" not in data:
            raise serializers.ValidationError("Formato esperado: { \"model\": \"app.model\", \"id\": \"uuid\" }.")
        app_label, _, model_name = data["model"].partition(".")
        try:
            ct = ContentType.objects.get_by_natural_key(app_label, model_name)
        except ContentType.DoesNotExist:
            raise serializers.ValidationError(f"Modelo desconhecido: {data['model']}")
        model = ct.model_class()
        if not model:
            raise serializers.ValidationError(f"Modelo sem classe: {data['model']}")
        if data["id"].lower() == "null":
            return None
        try:
            instance = model.objects.get(pk=data["id"])
        except model.DoesNotExist:
            raise serializers.ValidationError(f"Entidade não encontrada: {data['model']}:{data['id']}")
        return instance


class RelationshipSerializer(serializers.ModelSerializer):
    origin = EndpointField()
    target = EndpointField()
    type = serializers.ChoiceField(choices=RelationshipType.choices)

    class Meta:
        model = Relationship
        fields = ["id", "type", "origin", "target", "owner", "created_at", "updated_at"]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        origin = attrs.get("origin")
        target = attrs.get("target")

        if origin is None or target is None:
            raise serializers.ValidationError("origin e target são obrigatórios.")

        if origin == target:
            raise serializers.ValidationError("Uma entidade não pode se relacionar consigo mesma.")

        # Segurança: ambas as pontas precisam pertencer ao usuário logado (anti-IDOR).
        if user and user.is_authenticated:
            for endpoint, label in ((origin, "origin"), (target, "target")):
                owner_id = getattr(endpoint, "owner_id", None)
                if owner_id != user.id:
                    raise serializers.ValidationError(
                        {label: "Você só pode relacionar entidades suas."}
                    )

        return attrs

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        try:
            return super().create(validated_data)
        except Exception:
            raise serializers.ValidationError("Este relacionamento já existe.")
