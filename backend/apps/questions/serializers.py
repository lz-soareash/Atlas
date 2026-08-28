from rest_framework import serializers

from apps.core.serializers import OwnerModelSerializer
from .models import Question


class QuestionSerializer(OwnerModelSerializer):
    class Meta(OwnerModelSerializer.Meta):
        model = Question
        fields = OwnerModelSerializer.Meta.fields + [
            "question_text",
            "answered",
            "knowledge",
        ]
        read_only_fields = OwnerModelSerializer.Meta.read_only_fields + ["answered", "knowledge"]
