from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job", "match_score", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("candidate__email", "job__title")
