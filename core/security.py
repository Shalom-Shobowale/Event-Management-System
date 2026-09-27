import time
from collections import defaultdict
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.urls import resolve
from django.conf import settings


MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes

_failed_attempts = defaultdict(list)
_rate_limits = defaultdict(list)


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def is_rate_limited(ip, path, max_requests=20, window=60):
    now = time.time()
    key = f'{ip}:{path}'
    timestamps = _rate_limits[key]
    _rate_limits[key] = [t for t in timestamps if t > now - window]
    _rate_limits[key].append(now)
    return len(_rate_limits[key]) > max_requests


def record_failed_login(username, ip):
    now = time.time()
    key = f'{username}:{ip}'
    _failed_attempts[key] = [t for t in _failed_attempts[key] if t > now - LOCKOUT_DURATION]
    _failed_attempts[key].append(now)


def is_account_locked(username, ip):
    now = time.time()
    key = f'{username}:{ip}'
    _failed_attempts[key] = [t for t in _failed_attempts[key] if t > now - LOCKOUT_DURATION]
    return len(_failed_attempts[key]) >= MAX_FAILED_ATTEMPTS


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            ip = _get_client_ip(request)
            path = request.path

            if path in ('/login/', '/register/'):
                if is_rate_limited(ip, path, max_requests=10, window=60):
                    return JsonResponse(
                        {'error': 'Too many requests. Please try again later.'},
                        status=429,
                    )

            if is_rate_limited(ip, path, max_requests=30, window=60):
                return JsonResponse(
                    {'error': 'Too many requests. Please try again later.'},
                    status=429,
                )

        return self.get_response(request)
