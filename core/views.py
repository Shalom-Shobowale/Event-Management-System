from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Host
from core.security import record_failed_login, is_account_locked
from event.models import Event
from guest.models import Guest


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    events = (
        Event.objects
        .select_related('host')
        .filter(
            is_published=True,
            is_archived=False,
            is_suspended=False,
            date__gte=timezone.now(),
        )
        .order_by('date')[:6]   # ← the fix
    )

    return render(request, 'landing.html', {
        'events': events,
    })



def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        organization = request.POST.get('organization', '').strip()

        if not all([username, email, password, password2]):
            messages.error(request, 'All required fields must be filled.')
            return render(request, 'auth/register.html')

        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/register.html')

        if Host.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'auth/register.html')

        if Host.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'auth/register.html')

        user = Host.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            organization=organization,
        )
        login(request, user)
        messages.success(request, 'Welcome to EventFlow!')
        return redirect('dashboard')

    return render(request, 'auth/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember')

        ip = request.META.get('REMOTE_ADDR', '')
        if is_account_locked(username, ip):
            messages.error(request, 'Too many failed attempts. Please try again in 15 minutes.')
            return render(request, 'auth/login.html')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_suspended:
                messages.error(request, 'Your account has been suspended. Contact support for assistance.')
                return render(request, 'auth/login.html')
            login(request, user)
            if not remember:
                request.session.set_expiry(0)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('dashboard')
        record_failed_login(username, request.META.get('REMOTE_ADDR', ''))
        messages.error(request, 'Invalid credentials.')
    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('landing')


@login_required
def dashboard(request):
    from django.utils import timezone

    user = request.user
    now = timezone.now()

    # Base: host's own events (all of them, for stats)
    all_events = Event.objects.filter(host=user)

    # Stats
    total_events = all_events.count()
    total_guests = Guest.objects.filter(event__host=user).count()
    checked_in = Guest.objects.filter(event__host=user, checked_in=True).count()

    # Upcoming: future, not archived, not suspended — soonest first
    upcoming_qs = all_events.filter(
        date__gte=now,
        is_archived=False,
        is_suspended=False,
    )
    upcoming = upcoming_qs.count()
    upcoming_events = upcoming_qs.order_by('date')[:5]

    # Attendance rate
    attendance_rate = round(
        (checked_in / total_guests * 100) if total_guests > 0 else 0,
        1,
    )

    context = {
        'total_events': total_events,
        'total_guests': total_guests,
        'checked_in': checked_in,
        'upcoming': upcoming,
        'attendance_rate': attendance_rate,

        # The events shown in the "Next up" list
        'upcoming_events': upcoming_events,

        # Kept for backward-compat with any other template that uses them
        'events': all_events,
        'recent_events': upcoming_events,
    }
    return render(request, 'dashboard.html', context)



@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.phone = request.POST.get('phone', '').strip()
        user.organization = request.POST.get('organization', '').strip()
        user.bio = request.POST.get('bio', '').strip()
        user.email_notifications = bool(request.POST.get('email_notifications'))
        if request.FILES.get('avatar'):
            user.avatar = request.FILES['avatar']
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    return render(request, 'profile.html')


@login_required
def change_password_view(request):
    if request.method == 'POST':
        current = request.POST.get('current_password', '')
        new = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')

        if not request.user.check_password(current):
            messages.error(request, 'Current password is incorrect.')
            return render(request, 'change_password.html')

        if new != confirm:
            messages.error(request, 'New passwords do not match.')
            return render(request, 'change_password.html')

        request.user.set_password(new)
        request.user.save()
        login(request, request.user)
        messages.success(request, 'Password changed successfully.')
        return redirect('profile')

    return render(request, 'change_password.html')
