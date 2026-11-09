from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import employer_required

from .forms import JobForm, JobSearchForm
from .models import Job

PAGE_SIZE = 10


def job_list(request):
    """Public job search with filters and pagination (Module 4)."""
    form = JobSearchForm(request.GET or None)
    jobs = Job.objects.filter(status=Job.Status.OPEN)
    if form.is_valid():
        d = form.cleaned_data
        if d["q"]:
            jobs = jobs.filter(Q(title__icontains=d["q"]) | Q(description__icontains=d["q"])
                               | Q(company__icontains=d["q"]))
        if d["location"]:
            jobs = jobs.filter(location__icontains=d["location"])
        if d["job_type"]:
            jobs = jobs.filter(job_type=d["job_type"])
        if d["experience_level"]:
            jobs = jobs.filter(experience_level=d["experience_level"])
        if d["skill"]:
            jobs = jobs.filter(skills_required__icontains=d["skill"].strip().lower())
    page = Paginator(jobs, PAGE_SIZE).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "jobs/job_list.html",
                  {"form": form, "page": page, "query": query.urlencode()})


def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not job.is_open and not (request.user.is_authenticated and
                                (request.user == job.employer or request.user.is_portal_admin)):
        messages.info(request, "This job is no longer accepting applications.")
        return redirect("jobs:list")
    from applications.forms import ApplicationForm

    already_applied = (request.user.is_authenticated and request.user.is_candidate
                       and job.applications.filter(candidate=request.user).exists())
    return render(request, "jobs/job_detail.html", {
        "job": job, "form": ApplicationForm(), "already_applied": already_applied,
    })


@employer_required
def my_jobs(request):
    jobs = request.user.jobs.annotate(applicants=Count("applications"))
    return render(request, "jobs/my_jobs.html", {"jobs": jobs})


@employer_required
def job_create(request):
    form = JobForm(request.POST or None, initial={"company": request.user.company})
    if request.method == "POST" and form.is_valid():
        job = form.save(commit=False)
        job.employer = request.user
        job.save()
        messages.success(request, "Job posted.")
        return redirect("jobs:mine")
    return render(request, "jobs/job_form.html", {"form": form, "title": "Post a job"})


def _own_job(request, pk):
    return get_object_or_404(Job, pk=pk, employer=request.user)


@employer_required
def job_edit(request, pk):
    job = _own_job(request, pk)
    form = JobForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Job updated.")
        return redirect("jobs:mine")
    return render(request, "jobs/job_form.html", {"form": form, "title": "Edit job", "job": job})


@require_POST
@employer_required
def job_toggle(request, pk):
    job = _own_job(request, pk)
    job.status = Job.Status.CLOSED if job.is_open else Job.Status.OPEN
    job.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Job {'reopened' if job.is_open else 'closed'}.")
    return redirect("jobs:mine")


@require_POST
@employer_required
def job_delete(request, pk):
    job = _own_job(request, pk)
    job.delete()  # applications are deleted with it (cascade)
    messages.success(request, "Job and its applications deleted.")
    return redirect("jobs:mine")
