from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve


EXEMPT_PATHS = {'/login/', '/logout/', '/register/'}


class SuspendedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_suspended:
            path = request.path
            if path not in EXEMPT_PATHS and not path.startswith('/admin/'):
                from django.contrib.auth import logout
                logout(request)
                messages.error(request, 'Your account has been suspended. Contact support for assistance.')
                return redirect('login')
        return self.get_response(request)


