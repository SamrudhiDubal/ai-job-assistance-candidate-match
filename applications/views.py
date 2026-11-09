from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import candidate_required, employer_required
from jobs.models import Job

from .forms import ApplicationForm, StatusForm
from .models import Application
from .services import ApplyError, change_status, submit_application


@require_POST
@candidate_required
def apply(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    form = ApplicationForm(request.POST, request.FILES)
    if not form.is_valid():
        for errors in form.errors.values():
            for e in errors:
                messages.error(request, e)
        return redirect("jobs:detail", pk=job.pk)
    try:
        application = submit_application(job, request.user, form.cleaned_data["resume"],
                                         form.cleaned_data["cover_letter"])
    except ApplyError as exc:
        messages.error(request, str(exc))
        return redirect("jobs:detail", pk=job.pk)
    messages.success(request, f"Application submitted. Your match score is {application.match_score}%.")
    return redirect("applications:mine")


@candidate_required
def my_applications(request):
    apps = request.user.applications.select_related("job").order_by("-created_at")
    return render(request, "applications/my_applications.html", {"applications": apps})


@employer_required
def job_applicants(request, job_id):
    """Applicants for one of the employer's jobs, best match first (Module 8)."""
    job = get_object_or_404(Job, pk=job_id, employer=request.user)
    apps = job.applications.select_related("candidate").order_by("-match_score", "created_at")
    return render(request, "applications/applicants.html",
                  {"job": job, "applications": apps, "statuses": Application.Status.choices})


@require_POST
@employer_required
def update_status(request, pk):
    application = get_object_or_404(Application, pk=pk, job__employer=request.user)
    form = StatusForm(request.POST)
    if form.is_valid() and change_status(application, form.cleaned_data["status"]):
        messages.success(request, f"{application.candidate.name} marked as {application.get_status_display()}.")
    return redirect("applications:job_applicants", job_id=application.job_id)


def download_resume(request, pk):
    """Resumes are private: only the candidate, the job's employer or an admin can open one."""
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    application = get_object_or_404(Application, pk=pk)
    user = request.user
    if not (user == application.candidate or user == application.job.employer or user.is_portal_admin):
        raise PermissionDenied
    try:
        return FileResponse(application.resume.open("rb"), as_attachment=True,
                            filename=application.resume_original_name)
    except FileNotFoundError:
        raise Http404("Resume file not found")
