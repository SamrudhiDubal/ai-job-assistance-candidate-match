"""Business logic for applying to a job: parse, screen, save, notify."""
from django.db import IntegrityError, transaction

from screening import matcher
from screening.parsers import ResumeParseError, extract_text

from . import notifications
from .models import Application


class ApplyError(Exception):
    pass


def submit_application(job, candidate, resume_file, cover_letter=""):
    if not job.is_open:
        raise ApplyError("This job is closed.")
    if Application.objects.filter(job=job, candidate=candidate).exists():
        raise ApplyError("You have already applied for this job.")

    try:
        text = extract_text(resume_file, resume_file.name)
    except ResumeParseError as exc:
        raise ApplyError(str(exc)) from exc
    resume_file.seek(0)

    result = matcher.screen(text, job, declared_skills=candidate.skill_list)
    try:
        with transaction.atomic():
            application = Application.objects.create(
                job=job,
                candidate=candidate,
                resume=resume_file,
                resume_original_name=resume_file.name[:255],
                resume_text=text,
                cover_letter=cover_letter,
                extracted_skills=result["extracted_skills"],
                match_score=result["match_score"],
                match_details=result,
            )
    except IntegrityError as exc:
        raise ApplyError("You have already applied for this job.") from exc

    notifications.application_received(application)
    return application


def change_status(application, new_status):
    if new_status == application.status:
        return False
    application.status = new_status
    application.save(update_fields=["status", "updated_at"])
    notifications.status_changed(application)
    return True
