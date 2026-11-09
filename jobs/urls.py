from django.urls import path

from . import views

app_name = "jobs"
urlpatterns = [
    path("", views.job_list, name="list"),
    path("<int:pk>/", views.job_detail, name="detail"),
    path("mine/", views.my_jobs, name="mine"),
    path("new/", views.job_create, name="create"),
    path("<int:pk>/edit/", views.job_edit, name="edit"),
    path("<int:pk>/toggle/", views.job_toggle, name="toggle"),
    path("<int:pk>/delete/", views.job_delete, name="delete"),
]
