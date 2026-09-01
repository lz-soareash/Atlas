from rest_framework import serializers

from .models import ServiceCredential, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "type",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "type",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password_confirmation = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirmation",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password_confirmation"):
            raise serializers.ValidationError({"password_confirmation": "As senhas não conferem."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirmation")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ServiceCredentialSerializer(serializers.ModelSerializer):
    """Campos seguros de uma credencial de serviço.

    NUNCA expõe `key_hash` nem a chave em texto puro. A chave original é
    retornada apenas uma vez na criação/rotação, injetada manualmente na
    resposta pela view (não é um campo deste serializer).
    """

    class Meta:
        model = ServiceCredential
        fields = [
            "id",
            "name",
            "scopes",
            "key_hint",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "key_hint", "is_active", "created_at", "updated_at"]
