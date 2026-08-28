from django.contrib import admin

from .models import Decision


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "decided_at", "owner", "created_at"]
    list_filter = ["status"]
    search_fields = ["title", "decision", "rationale"]
