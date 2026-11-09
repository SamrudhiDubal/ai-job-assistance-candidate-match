from django.urls import path

from . import views

app_name = "adminpanel"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("users/<int:pk>/toggle/", views.user_toggle, name="user_toggle"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),
    path("jobs/<int:pk>/toggle/", views.job_toggle, name="job_toggle"),
    path("jobs/<int:pk>/delete/", views.job_delete, name="job_delete"),
]
