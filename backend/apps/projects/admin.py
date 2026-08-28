from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "owner", "created_at"]
    list_filter = ["status"]
    search_fields = ["name", "description", "objective"]
