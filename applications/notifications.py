"""Email notifications (Module 9). Failures are logged and never break a request."""
import logging

from django.core.mail import send_mail

log = logging.getLogger("jobmatch.mail")


def _send(subject, body, to):
    try:
        send_mail(subject, body, None, [to])
    except Exception:  # SMTP down, bad credentials, etc.
        log.exception("Could not send email to %s", to)


def application_received(application):
    job, cand = application.job, application.candidate
    _send(
        f"New applicant for {job.title}",
        f"{cand.name} applied for {job.title}.\nAI match score: {application.match_score}%\n"
        f"Open the applicants page to review the ranking.",
        job.employer.email,
    )
    _send(
        f"Application submitted: {job.title}",
        f"Hi {cand.name},\n\nYour application for {job.title} at {job.company} was received.\n"
        f"Your match score is {application.match_score}%. We'll email you when the status changes.",
        cand.email,
    )


def status_changed(application):
    job, cand = application.job, application.candidate
    _send(
        f"Update on your application: {job.title}",
        f"Hi {cand.name},\n\nThe status of your application for {job.title} at {job.company} "
        f"is now: {application.get_status_display()}.",
        cand.email,
    )
