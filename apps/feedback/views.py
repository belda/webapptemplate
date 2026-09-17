from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import BugReportForm
from .models import BugReport


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


@login_required
@require_http_methods(["GET", "POST"])
def bug_report_modal(request):
    if request.method == "POST":
        form = BugReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user if request.user.is_authenticated else None
            report.workspace = getattr(request, "workspace", None)
            report.page_url = (request.POST.get("page_url") or "")[:500]
            report.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
            report.ip_address = _client_ip(request)
            if not report.contact_email and request.user.is_authenticated:
                report.contact_email = request.user.email or ""
            report.save()
            reload_page = reverse("feedback:my_reports") in report.page_url
            return render(
                request,
                "feedback/_bug_report_thanks.html",
                {"reload_page": reload_page},
            )
    else:
        initial = {}
        if request.user.is_authenticated and request.user.email:
            initial["contact_email"] = request.user.email
        form = BugReportForm(initial=initial)

    return render(
        request,
        "feedback/_bug_report_modal.html",
        {"form": form, "page_url": request.META.get("HTTP_REFERER", "")},
    )


@login_required
def bug_report_dismiss(request):
    return HttpResponse("")


@login_required
def my_reports(request):
    reports = (
        BugReport.objects.filter(user=request.user)
        .prefetch_related("updates")
        .order_by("-created_at")
    )
    open_count = sum(1 for report in reports if report.is_open)
    return render(
        request,
        "feedback/my_reports.html",
        {"reports": reports, "open_count": open_count},
    )
