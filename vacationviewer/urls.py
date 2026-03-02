"""Root URL configuration for VacationViewer."""

from django.urls import include, path

urlpatterns: list = [
    path("", include("screen.urls")),
]
