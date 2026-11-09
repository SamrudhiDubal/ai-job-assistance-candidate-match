from django.conf import settings
from django.db import models


class Job(models.Model):
    """A job posting created by an employer (Module 3)."""

    class JobType(models.TextChoices):
        FULL_TIME = "full-time", "Full-time"
        PART_TIME = "part-time", "Part-time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"

    class Level(models.TextChoices):
        ENTRY = "entry", "Entry"
        MID = "mid", "Mid"
        SENIOR = "senior", "Senior"
        LEAD = "lead", "Lead"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    title = models.CharField(max_length=150)
    company = models.CharField(max_length=150)
    description = models.TextField()
    location = models.CharField(max_length=120, default="Remote")
    job_type = models.CharField(max_length=12, choices=JobType.choices, default=JobType.FULL_TIME)
    experience_level = models.CharField(max_length=8, choices=Level.choices, default=Level.ENTRY)
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    skills_required = models.TextField(help_text="Comma-separated list, e.g. python, django, sql")
    employer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jobs")
    status = models.CharField(max_length=6, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} at {self.company}"

    def save(self, *args, **kwargs):
        # Required skills are stored lowercase and de-duplicated.
        seen = []
        for s in self.skills_required.split(","):
            s = s.strip().lower()
            if s and s not in seen:
                seen.append(s)
        self.skills_required = ", ".join(seen)
        super().save(*args, **kwargs)

    @property
    def skill_list(self):
        return [s.strip() for s in self.skills_required.split(",") if s.strip()]

    @property
    def is_open(self):
        return self.status == self.Status.OPEN
