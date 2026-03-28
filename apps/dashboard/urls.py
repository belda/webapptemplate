from django.urls import path
from .views import dashboard, home

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("", home, name="home"),
]
