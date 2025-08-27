"""
URL configuration for Athena DRF project.

The ``urlpatterns`` list routes URLs to views.  It includes the Django
admin and the API URLs defined in the ``api`` app.  You can also add
additional top‑level routes here as needed.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]