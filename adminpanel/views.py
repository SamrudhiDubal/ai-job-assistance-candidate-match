"""Administrator dashboard (Module 10): overview, users, jobs, applications."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.models import User
from applications.models import Application
from jobs.models import Job


@admin_required
def dashboard(request):
    tab = request.GET.get("tab", "overview")
    ctx = {"tab": tab}
    if tab == "users":
        users = User.objects.order_by("-date_joined")
        q, role = request.GET.get("q", "").strip(), request.GET.get("role", "")
        if q:
            users = users.filter(Q(name__icontains=q) | Q(email__icontains=q))
        if role:
            users = users.filter(role=role)
        ctx.update(page=Paginator(users, 20).get_page(request.GET.get("page")), q=q, role=role,
                   roles=User.Role.choices)
    elif tab == "jobs":
        ctx["page"] = Paginator(Job.objects.select_related("employer"), 20).get_page(request.GET.get("page"))
    elif tab == "applications":
        apps = Application.objects.select_related("job", "candidate").order_by("-created_at")
        ctx["page"] = Paginator(apps, 20).get_page(request.GET.get("page"))
    else:
        ctx["stats"] = {
            "Total users": User.objects.count(),
            "Candidates": User.objects.filter(role=User.Role.CANDIDATE).count(),
            "Employers": User.objects.filter(role=User.Role.EMPLOYER).count(),
            "Total jobs": Job.objects.count(),
            "Open jobs": Job.objects.filter(status=Job.Status.OPEN).count(),
            "Applications": Application.objects.count(),
            "Average match score": round(Application.objects.aggregate(a=Avg("match_score"))["a"] or 0, 1),
            "Shortlisted": Application.objects.filter(status=Application.Status.SHORTLISTED).count(),
        }
    return render(request, "adminpanel/dashboard.html", ctx)


@require_POST
@admin_required
def user_toggle(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(request, f"{user.email} {'activated' if user.is_active else 'deactivated'}.")
    return redirect("/admin-panel/?tab=users")


@require_POST
@admin_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
    else:
        user.delete()  # their jobs and applications go with them
        messages.success(request, "User deleted.")
    return redirect("/admin-panel/?tab=users")


@require_POST
@admin_required
def job_toggle(request, pk):
    job = get_object_or_404(Job, pk=pk)
    job.status = Job.Status.CLOSED if job.is_open else Job.Status.OPEN
    job.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Job {'reopened' if job.is_open else 'closed'}.")
    return redirect("/admin-panel/?tab=jobs")


@require_POST
@admin_required
def job_delete(request, pk):
    get_object_or_404(Job, pk=pk).delete()
    messages.success(request, "Job deleted.")
    return redirect("/admin-panel/?tab=jobs")
