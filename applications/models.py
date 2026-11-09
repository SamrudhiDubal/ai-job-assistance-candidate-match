import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


def resume_upload_path(instance, filename):
    # Random file name so uploaded names can never clash or be guessed.
    return f"resumes/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Application(models.Model):
    """A candidate's application to a job, with its AI screening result."""

    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        HIRED = "hired", "Hired"

    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="applications")
    resume = models.FileField(upload_to=resume_upload_path)
    resume_original_name = models.CharField(max_length=255)
    resume_text = models.TextField()
    cover_letter = models.TextField(blank=True)
    extracted_skills = models.JSONField(default=list)
    match_score = models.PositiveSmallIntegerField(default=0)
    match_details = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.APPLIED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-match_score", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["job", "candidate"], name="one_application_per_job"),
        ]

    def __str__(self):
        return f"{self.candidate} -> {self.job} ({self.match_score})"

    @property
    def score_band(self):
        """Colour band for the match badge."""
        if self.match_score >= 75:
            return "success"
        if self.match_score >= 50:
            return "warning"
        return "danger"
