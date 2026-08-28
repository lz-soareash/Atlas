from django.contrib import admin

from .models import Knowledge


@admin.register(Knowledge)
class KnowledgeAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "domain_level", "owner", "created_at"]
    list_filter = ["status", "domain_level"]
    search_fields = ["title", "summary", "content"]
