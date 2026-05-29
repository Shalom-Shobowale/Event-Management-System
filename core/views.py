from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Host
from event.models import Event
from guest.models import Guest


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


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

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if not remember:
                request.session.set_expiry(0)

            messages.success(
                request,
                f'Welcome back, {user.get_full_name() or user.username}!'
            )

            # Redirect to intended page
            next_url = request.POST.get('next')

            if next_url:
                return redirect(next_url)

            return redirect('dashboard')

        messages.error(request, 'Invalid credentials.')

    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('landing')


@login_required
def dashboard(request):
    user = request.user

    # Check if user has a vendor profile - redirect to vendor dashboard
    if hasattr(user, 'vendor_profile'):
        from vendors.models import Service
        vendor = user.vendor_profile
        services = vendor.services.all()[:5]
        recent_reviews = vendor.reviews.all()[:3]
        context = {
            'vendor': vendor,
            'services': services,
            'recent_reviews': recent_reviews,
            'total_services': vendor.services.count(),
            'total_portfolio': vendor.portfolio.count(),
        }
        return render(request, 'vendors/dashboard.html', context)

    # Regular host dashboard
    events = Event.objects.filter(host=user)
    total_events = events.count()
    total_guests = Guest.objects.filter(event__host=user).count()
    checked_in = Guest.objects.filter(event__host=user, checked_in=True).count()
    upcoming = events.filter(date__gte=timezone.now()).count()
    attendance_rate = round((checked_in / total_guests * 100) if total_guests > 0 else 0, 1)
    recent_events = events[:5]

    context = {
        'total_events': total_events,
        'total_guests': total_guests,
        'checked_in': checked_in,
        'upcoming': upcoming,
        'attendance_rate': attendance_rate,
        'recent_events': recent_events,
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
