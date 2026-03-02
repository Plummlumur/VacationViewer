"""URL configuration for the screen app."""

from django.urls import path

from screen import admin_views, views

urlpatterns: list = [
    path("", views.month_screen, name="month_screen"),
    path("health/", views.health, name="health"),
    path("admin/login/", admin_views.admin_login, name="admin_login"),
    path("admin/logout/", admin_views.admin_logout, name="admin_logout"),
    path("admin/dashboard/", admin_views.admin_dashboard, name="admin_dashboard"),
    path("admin/", admin_views.admin_login, name="admin"),
]
