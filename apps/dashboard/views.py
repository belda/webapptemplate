from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


@login_required
def dashboard(request):
    return render(request, "dashboard/dashboard.html")
