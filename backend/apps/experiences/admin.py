from django.contrib import admin

from .models import Experience


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "status", "owner", "created_at"]
    list_filter = ["kind", "status"]
    search_fields = ["title", "content"]
