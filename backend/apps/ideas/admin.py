from django.contrib import admin

from .models import Idea


@admin.register(Idea)
class IdeaAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "converted", "owner", "created_at"]
    list_filter = ["status", "converted"]
    search_fields = ["title", "description"]
