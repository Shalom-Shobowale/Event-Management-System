from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'admin_role'):
            messages.error(request, 'You do not have access to the admin panel.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def permission_required(permission):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if not hasattr(request.user, 'admin_role'):
                messages.error(request, 'You do not have access to the admin panel.')
                return redirect('dashboard')
            if permission not in request.user.admin_role.permissions:
                messages.error(request, f'You do not have permission: {permission}')
                return redirect('admin_dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
