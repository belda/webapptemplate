from django.urls import path

from . import views

app_name = "feedback"

urlpatterns = [
    path("report/", views.bug_report_modal, name="bug_report_modal"),
    path("report/dismiss/", views.bug_report_dismiss, name="bug_report_dismiss"),
    path("reports/", views.my_reports, name="my_reports"),
]
