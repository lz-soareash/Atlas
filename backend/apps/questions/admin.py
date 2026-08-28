from django.contrib import admin

from .models import Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "answered", "owner", "created_at"]
    list_filter = ["status", "answered"]
    search_fields = ["title", "question_text"]
