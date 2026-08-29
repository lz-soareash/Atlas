from django.contrib import admin

from .models import InboxItem


@admin.register(InboxItem)
class InboxItemAdmin(admin.ModelAdmin):
    list_display = ("content", "status", "kind", "owner", "created_at")
    list_filter = ("status", "kind")
    readonly_fields = ("owner",)
