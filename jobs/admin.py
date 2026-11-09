from django.contrib import admin

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "employer", "experience_level", "status", "created_at")
    list_filter = ("status", "job_type", "experience_level")
    search_fields = ("title", "company", "description")
