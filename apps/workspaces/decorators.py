from functools import wraps
from django.core.exceptions import PermissionDenied
from .models import Membership


def workspace_member_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        workspace = request.workspace
        if not workspace:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def workspace_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        workspace = request.workspace
        if not workspace:
            raise PermissionDenied
        try:
            membership = Membership.objects.get(user=request.user, workspace=workspace)
            if not membership.is_admin:
                raise PermissionDenied
        except Membership.DoesNotExist:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
