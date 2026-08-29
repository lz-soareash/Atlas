from django.contrib import admin

from .models import Relationship


@admin.register(Relationship)
class RelationshipAdmin(admin.ModelAdmin):
    list_display = ["__str__", "type", "owner", "created_at"]
    list_filter = ["type"]
    search_fields = ["origin_id", "target_id"]
