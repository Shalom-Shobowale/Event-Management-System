import json
from datetime import timedelta
from venv import logger
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import (
    Avg, Case, Count, DecimalField, IntegerField, Q, Sum, Value, When,
)
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal

from core.models import Host
from event.models import Event
from guest.models import Guest
from vendors.models import Vendor, VendorReview
from bookings.models import Booking, QuoteRequest, Proposal
from ticket.models import CheckInLog
from collaboration.models import ActivityLog
from payments.models import HostPaymentAccount
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import (
    AdminRole, AuditLog, Report, SupportTicket, TicketReply,
    PlatformNotification, PlatformSettings, ServiceCategory,
    FeaturedVendor, SecurityEvent,
)
from .decorators import admin_required, permission_required
from django.db.models.functions import Coalesce
from .services import log_action


# ==================== DASHBOARD ====================

@admin_required
def admin_dashboard(request):
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    total_hosts = Host.objects.filter(vendor_profile__isnull=True, is_superuser=False, is_staff=False).count()
    total_vendors = Vendor.objects.count()
    total_events = Event.objects.count()
    total_guests = Guest.objects.count()
    active_events = Event.objects.filter(date__gt=now, is_suspended=False, is_archived=False).count()
    completed_events = Event.objects.filter(date__lt=now).count()
    pending_vendor_verifications = Vendor.objects.filter(verification_status=Vendor.VerificationStatus.PENDING).count()
    pending_host_verifications = Host.objects.filter(verification_level=0, is_suspended=False, vendor_profile__isnull=True).exclude(is_superuser=True).count()

    recent_hosts = Host.objects.filter(created_at__gte=thirty_days_ago, vendor_profile__isnull=True).count()
    prev_hosts = Host.objects.filter(created_at__lt=thirty_days_ago, vendor_profile__isnull=True).count()
    host_growth = ((recent_hosts - prev_hosts) / prev_hosts * 100) if prev_hosts > 0 else 100

    recent_vendors = Vendor.objects.filter(created_at__gte=thirty_days_ago).count()
    prev_vendors = Vendor.objects.filter(created_at__lt=thirty_days_ago).count()
    vendor_growth = ((recent_vendors - prev_vendors) / prev_vendors * 100) if prev_vendors > 0 else 100

    recent_events = Event.objects.filter(created_at__gte=thirty_days_ago).count()
    prev_events = Event.objects.filter(created_at__lt=thirty_days_ago).count()
    event_growth = ((recent_events - prev_events) / prev_events * 100) if prev_events > 0 else 100

    recent_guests = Guest.objects.filter(registered_at__gte=thirty_days_ago).count()
    prev_guests = Guest.objects.filter(registered_at__lt=thirty_days_ago).count()
    guest_growth = ((recent_guests - prev_guests) / prev_guests * 100) if prev_guests > 0 else 100

    # Monthly growth data for charts
    months = []
    hosts_data = []
    vendors_data = []
    events_data = []
    guests_data = []
    for i in range(6, -1, -1):
        month_start = now.replace(day=1) - timedelta(days=30 * i)
        month_end = month_start + timedelta(days=30)
        months.append(month_start.strftime('%b'))
        hosts_data.append(Host.objects.filter(created_at__lt=month_end, vendor_profile__isnull=True).count())
        vendors_data.append(Vendor.objects.filter(created_at__lt=month_end).count())
        events_data.append(Event.objects.filter(created_at__lt=month_end).count())
        guests_data.append(Guest.objects.filter(registered_at__lt=month_end).count())

    # Recent activity feed
    recent_activity = AuditLog.objects.select_related('actor')[:15]

    # Pending reports count
    pending_reports = Report.objects.filter(status__in=['pending', 'reviewing']).count()
    open_tickets = SupportTicket.objects.filter(status__in=['open', 'pending']).count()
    security_events = SecurityEvent.objects.filter(is_resolved=False).count()

    # Revenue estimate (sum of all booking agreed prices for completed bookings)
    total_revenue = Booking.objects.filter(status=Booking.Status.COMPLETED).aggregate(
        total=Count('id')
    )['total'] or 0

    context = {
        'total_hosts': total_hosts,
        'total_vendors': total_vendors,
        'total_events': total_events,
        'total_guests': total_guests,
        'active_events': active_events,
        'completed_events': completed_events,
        'pending_vendor_verifications': pending_vendor_verifications,
        'pending_host_verifications': pending_host_verifications,
        'host_growth': round(host_growth, 1),
        'vendor_growth': round(vendor_growth, 1),
        'event_growth': round(event_growth, 1),
        'guest_growth': round(guest_growth, 1),
        'months_json': json.dumps(months),
        'hosts_json': json.dumps(hosts_data),
        'vendors_json': json.dumps(vendors_data),
        'events_json': json.dumps(events_data),
        'guests_json': json.dumps(guests_data),
        'recent_activity': recent_activity,
        'pending_reports': pending_reports,
        'open_tickets': open_tickets,
        'security_events': security_events,
        'total_revenue': total_revenue,
    }
    return render(request, 'admin_panel/dashboard.html', context)


# ==================== USER MANAGEMENT ====================

@admin_required
@permission_required('manage_users')
def admin_users(request):
    user_type = request.GET.get('type', 'all')
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    users = Host.objects.select_related('vendor_profile', 'admin_role').all()

    if user_type == 'hosts':
        users = users.filter(vendor_profile__isnull=True, is_staff=False, is_superuser=False)
    elif user_type == 'vendors':
        users = users.filter(vendor_profile__isnull=False)
    elif user_type == 'staff':
        users = users.filter(is_staff=True)
    elif user_type == 'admins':
        users = users.filter(admin_role__isnull=False)

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    if status == 'suspended':
        users = users.filter(is_suspended=True)
    elif status == 'active':
        users = users.filter(is_suspended=False)
    elif status == 'verified':
        users = users.filter(verification_level__gte=1)

    users = users.order_by('-created_at')[:100]

    context = {
        'users': users,
        'user_type': user_type,
        'search': search,
        'status': status,
    }
    return render(request, 'admin_panel/users.html', context)


@admin_required
@permission_required('manage_users')
def admin_user_detail(request, user_id):
    user = get_object_or_404(Host.objects.select_related('vendor_profile', 'admin_role'), id=user_id)
    user_events = Event.objects.filter(host=user).order_by('-date')[:10]
    user_reports = Report.objects.filter(Q(reporter=user) | Q(target_id=str(user.id))).order_by('-created_at')[:10]
    user_tickets = SupportTicket.objects.filter(user=user).order_by('-created_at')[:5]
    user_audit = AuditLog.objects.filter(actor=user).order_by('-created_at')[:10]

    context = {
        'target_user': user,
        'user_events': user_events,
        'user_reports': user_reports,
        'user_tickets': user_tickets,
        'user_audit': user_audit,
    }
    return render(request, 'admin_panel/user_detail.html', context)


@admin_required
@permission_required('manage_users')
def admin_user_action(request, user_id):
    if request.method != 'POST':
        return redirect('admin_users')

    user = get_object_or_404(Host, id=user_id)
    action = request.POST.get('action')
    reason = request.POST.get('reason', '')

    if action == 'suspend':
        user.is_suspended = True
        user.suspended_at = timezone.now()
        user.suspended_by = request.user
        user.suspension_reason = reason
        user.save(update_fields=['is_suspended', 'suspended_at', 'suspended_by', 'suspension_reason'])
        log_action(request.user, AuditLog.Action.HOST_SUSPENDED, 'Host', user.id,
                   f'Suspended {user.username}. Reason: {reason}')
        messages.success(request, f'{user.username} has been suspended.')
    elif action == 'activate':
        user.is_suspended = False
        user.suspended_at = None
        user.suspended_by = None
        user.suspension_reason = ''
        user.save(update_fields=['is_suspended', 'suspended_at', 'suspended_by', 'suspension_reason'])
        log_action(request.user, AuditLog.Action.HOST_ACTIVATED, 'Host', user.id,
                   f'Activated {user.username}')
        messages.success(request, f'{user.username} has been activated.')
    elif action == 'verify':
        level = int(request.POST.get('level', 1))
        user.verification_level = level
        if level >= 2:
            user.phone_verified = True
        user.save(update_fields=['verification_level', 'phone_verified'])
        log_action(request.user, AuditLog.Action.HOST_VERIFIED, 'Host', user.id,
                   f'Verified {user.username} to level {level}')
        messages.success(request, f'{user.username} verification level set to {level}.')
    elif action == 'delete':
        if user.id == request.user.id:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('admin_user_detail', user_id=user_id)
        username = user.username
        user.delete()
        log_action(request.user, AuditLog.Action.USER_DELETED, 'Host', user_id,
                   f'Deleted user {username}')
        messages.success(request, f'User {username} has been deleted.')
        return redirect('admin_users')

    return redirect('admin_user_detail', user_id=user_id)


# ==================== HOST VERIFICATION ====================

@admin_required
@permission_required('manage_users')
def admin_host_verification(request):
    search = request.GET.get('search', '')
    level = request.GET.get('level', '')

    hosts = Host.objects.filter(vendor_profile__isnull=True, is_staff=False, is_superuser=False).select_related('admin_role')

    if level:
        hosts = hosts.filter(verification_level=int(level))

    if search:
        hosts = hosts.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(organization__icontains=search)
        )

    hosts = hosts.annotate(
        event_count=Count('events')
    ).order_by('verification_level', '-created_at')[:100]

    # Counts per verification level
    level_counts_raw = (
        Host.objects
        .filter(vendor_profile__isnull=True, is_staff=False, is_superuser=False)
        .values('verification_level')
        .annotate(count=Count('id'))
    )
    level_counts = {row['verification_level']: row['count'] for row in level_counts_raw}

    # Convert to a list of dicts so the template can loop over it
    level_counts_list = [
        {'level': 0, 'count': level_counts.get(0, 0)},
        {'level': 1, 'count': level_counts.get(1, 0)},
        {'level': 2, 'count': level_counts.get(2, 0)},
        {'level': 3, 'count': level_counts.get(3, 0)},
    ]

    context = {
        'hosts': hosts,
        'search': search,
        'level': level,
        'level_counts': level_counts_list,
    }
    return render(request, 'admin_panel/host_verification.html', context)


# ==================== VENDOR VERIFICATION ====================

@admin_required
@permission_required('manage_vendors')
def admin_vendor_verification(request):
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    vendors = Vendor.objects.select_related('user').all()

    if status:
        vendors = vendors.filter(verification_status=status)

    if search:
        vendors = vendors.filter(
            Q(business_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(city__icontains=search)
        )

    vendors = vendors.order_by('verification_status', '-created_at')[:100]

    context = {
        'vendors': vendors,
        'search': search,
        'status': status,
    }
    return render(request, 'admin_panel/vendor_verification.html', context)


@admin_required
@permission_required('manage_vendors')
def admin_vendor_detail(request, vendor_id):
    vendor = get_object_or_404(Vendor.objects.select_related('user'), id=vendor_id)
    services = vendor.services.all()
    portfolio = vendor.portfolio.all()[:12]
    reviews = vendor.reviews.select_related('reviewer').all()[:10]
    bookings = Booking.objects.filter(vendor=vendor).select_related('event').order_by('-created_at')[:10]
    reports = Report.objects.filter(target_id=str(vendor.id)).order_by('-created_at')[:5]

    context = {
        'vendor': vendor,
        'services': services,
        'portfolio': portfolio,
        'reviews': reviews,
        'bookings': bookings,
        'reports': reports,
    }
    return render(request, 'admin_panel/vendor_detail.html', context)


@admin_required
@permission_required('manage_vendors')
def admin_vendor_action(request, vendor_id):
    if request.method != 'POST':
        return redirect('admin_vendor_verification')

    vendor = get_object_or_404(Vendor, id=vendor_id)
    action = request.POST.get('action')
    reason = request.POST.get('reason', '')

    if action == 'approve':
        vendor.verification_status = Vendor.VerificationStatus.VERIFIED
        vendor.verified_at = timezone.now()
        vendor.save(update_fields=['verification_status', 'verified_at'])
        log_action(request.user, AuditLog.Action.VENDOR_APPROVED, 'Vendor', vendor.id,
                   f'Approved vendor {vendor.business_name}')
        messages.success(request, f'{vendor.business_name} has been verified.')
    elif action == 'reject':
        vendor.verification_status = Vendor.VerificationStatus.REJECTED
        vendor.save(update_fields=['verification_status'])
        log_action(request.user, AuditLog.Action.VENDOR_REJECTED, 'Vendor', vendor.id,
                   f'Rejected vendor {vendor.business_name}. Reason: {reason}')
        messages.success(request, f'{vendor.business_name} has been rejected.')
    elif action == 'pending':
        vendor.verification_status = Vendor.VerificationStatus.PENDING
        vendor.save(update_fields=['verification_status'])
        messages.success(request, f'{vendor.business_name} set to pending review.')
    elif action == 'suspend':
        vendor.is_suspended = True
        vendor.suspended_at = timezone.now()
        vendor.suspended_by = request.user
        vendor.suspension_reason = reason
        vendor.save(update_fields=['is_suspended', 'suspended_at', 'suspended_by', 'suspension_reason'])
        log_action(request.user, AuditLog.Action.VENDOR_SUSPENDED, 'Vendor', vendor.id,
                   f'Suspended vendor {vendor.business_name}. Reason: {reason}')
        messages.success(request, f'{vendor.business_name} has been suspended.')
    elif action == 'activate':
        vendor.is_suspended = False
        vendor.suspended_at = None
        vendor.suspended_by = None
        vendor.suspension_reason = ''
        vendor.save(update_fields=['is_suspended', 'suspended_at', 'suspended_by', 'suspension_reason'])
        messages.success(request, f'{vendor.business_name} has been activated.')
    elif action == 'badge':
        badge = request.POST.get('badge', Vendor.Badge.NONE)
        vendor.badge = badge
        vendor.save(update_fields=['badge'])
        log_action(request.user, AuditLog.Action.VENDOR_BADGE, 'Vendor', vendor.id,
                   f'Changed badge for {vendor.business_name} to {badge}')
        messages.success(request, f'Badge updated for {vendor.business_name}.')
    elif action == 'notes':
        vendor.admin_notes = request.POST.get('admin_notes', '')
        vendor.save(update_fields=['admin_notes'])
        messages.success(request, 'Admin notes saved.')

    return redirect('admin_vendor_detail', vendor_id=vendor_id)


# ==================== EVENT MONITORING ====================

@admin_required
@permission_required('manage_events')
def admin_events(request):
    """
    Event monitoring with production-grade querying.

    Production notes:
    - Paginated at 25/page (events are heavy rows)
    - Count annotations use distinct=True to avoid cartesian double-counting
    - admin_flags filtering handles both [] and null defaults
    - Visibility filter (draft / unlisted / public) reflects is_published + is_listed
    - All filters indexed at the DB level (verify with `python manage.py check`)
    """
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    category_filter = request.GET.get('category', '').strip()
    page_number = request.GET.get('page', 1)
    now = timezone.now()

    # ---- Base queryset ----
    events_qs = (
        Event.objects
        .select_related('host')
        .all()
    )

    # ---- Status filter ----
    if status_filter == 'active':
        events_qs = events_qs.filter(
            date__gt=now, is_suspended=False, is_archived=False
        )
    elif status_filter == 'completed':
        events_qs = events_qs.filter(date__lt=now, is_archived=False)
    elif status_filter == 'suspended':
        events_qs = events_qs.filter(is_suspended=True)
    elif status_filter == 'archived':
        events_qs = events_qs.filter(is_archived=True)
    elif status_filter == 'flagged':
        # Handles both `[]` (empty list default) and `null` correctly.
        # Excludes events whose admin_flags is an empty list OR null.
        events_qs = events_qs.exclude(
            Q(admin_flags=[]) | Q(admin_flags__isnull=True)
        )
    # ---- Visibility filters ----
    elif status_filter == 'public':
        events_qs = events_qs.filter(is_published=True, is_listed=True)
    elif status_filter == 'unlisted':
        events_qs = events_qs.filter(is_published=True, is_listed=False)
    elif status_filter == 'draft':
        events_qs = events_qs.filter(is_published=False)

    # ---- Category filter ----
    if category_filter:
        events_qs = events_qs.filter(category=category_filter)

    # ---- Search ----
    if search:
        events_qs = events_qs.filter(
            Q(name__icontains=search) |
            Q(venue__icontains=search) |
            Q(host__username__icontains=search) |
            Q(host__email__icontains=search)
        )

    # ---- Counts: distinct=True prevents cartesian inflation ----
    events_qs = events_qs.annotate(
        guest_count=Count('guests', distinct=True),
        booking_count=Count('bookings', distinct=True),
    ).order_by('-date')

    # ---- Pagination ----
    paginator = Paginator(events_qs, 25)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # After pagination, annotate each event with display states
    for event in page_obj:
        # Operational state
        if event.is_suspended:
            event.display_status = 'suspended'
        elif event.is_archived:
            event.display_status = 'archived'
        elif event.date > now:
            event.display_status = 'active'
        else:
            event.display_status = 'completed'

        # Visibility state
        if not event.is_published:
            event.visibility = 'draft'
        elif event.is_listed:
            event.visibility = 'public'
        else:
            event.visibility = 'unlisted'

    # ---- Stat strip counts (single query each) ----
    stat_base = Event.objects.all()

    active_count = stat_base.filter(
        date__gt=now, is_suspended=False, is_archived=False
    ).count()
    completed_count = stat_base.filter(
        date__lt=now, is_archived=False
    ).count()
    suspended_count = stat_base.filter(is_suspended=True).count()
    archived_count = stat_base.filter(is_archived=True).count()

    # Flagged: events with non-empty admin_flags
    flagged_count = stat_base.exclude(
        Q(admin_flags=[]) | Q(admin_flags__isnull=True)
    ).count()

    # ---- Visibility counts ----
    public_count = stat_base.filter(is_published=True, is_listed=True).count()
    unlisted_count = stat_base.filter(is_published=True, is_listed=False).count()
    draft_count = stat_base.filter(is_published=False).count()

    # ---- Category list for the filter dropdown ----
    # Only show categories that actually have events
    category_choices = (
        Event.objects
        .exclude(category='')
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )

    context = {
        'events': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'category_choices': category_choices,
        'active_count': active_count,
        'completed_count': completed_count,
        'suspended_count': suspended_count,
        'archived_count': archived_count,
        'flagged_count': flagged_count,
        'public_count': public_count,
        'unlisted_count': unlisted_count,
        'draft_count': draft_count,
        'total_count': paginator.count,
    }
    return render(request, 'admin_panel/events.html', context)

@admin_required
@permission_required('manage_events')
def admin_event_action(request, event_id):
    if request.method != 'POST':
        return redirect('admin_events')

    event = get_object_or_404(Event, id=event_id)
    action = request.POST.get('action')
    reason = request.POST.get('reason', '')

    if action == 'suspend':
        event.is_suspended = True
        event.suspended_at = timezone.now()
        event.suspended_by = request.user
        event.save(update_fields=['is_suspended', 'suspended_at', 'suspended_by'])
        flags = event.admin_flags or []
        flags.append({'type': 'suspended', 'reason': reason, 'by': request.user.username, 'at': timezone.now().isoformat()})
        event.admin_flags = flags
        event.save(update_fields=['admin_flags'])
        log_action(request.user, AuditLog.Action.EVENT_SUSPENDED, 'Event', event.id,
                   f'Suspended event {event.name}. Reason: {reason}')
        messages.success(request, f'{event.name} has been suspended.')
    elif action == 'activate':
        event.is_suspended = False
        event.suspended_at = None
        event.suspended_by = None
        event.save(update_fields=['is_suspended', 'suspended_at', 'suspended_by'])
        messages.success(request, f'{event.name} has been activated.')
    elif action == 'archive':
        event.is_archived = True
        event.save(update_fields=['is_archived'])
        log_action(request.user, AuditLog.Action.EVENT_ARCHIVED, 'Event', event.id,
                   f'Archived event {event.name}')
        messages.success(request, f'{event.name} has been archived.')
    elif action == 'unarchive':
        event.is_archived = False
        event.save(update_fields=['is_archived'])
        messages.success(request, f'{event.name} has been unarchived.')
    elif action == 'flag':
        flag_type = request.POST.get('flag_type', 'suspicious')
        flags = event.admin_flags or []
        flags.append({'type': flag_type, 'reason': reason, 'by': request.user.username, 'at': timezone.now().isoformat()})
        event.admin_flags = flags
        event.save(update_fields=['admin_flags'])
        log_action(request.user, AuditLog.Action.EVENT_REVIEWED, 'Event', event.id,
                   f'Flagged event {event.name} as {flag_type}. Reason: {reason}')
        messages.success(request, f'{event.name} has been flagged.')

    return redirect('admin_events')


# ==================== REPORTS & TRUST CENTER ====================

@admin_required
@permission_required('manage_reports')
def admin_reports(request):
    status = request.GET.get('status', '')
    category = request.GET.get('category', '')

    reports = Report.objects.select_related('reporter', 'assigned_to', 'resolved_by').all()

    if status:
        reports = reports.filter(status=status)

    if category:
        reports = reports.filter(category=category)

    reports = reports.order_by('-created_at')[:100]

    context = {
        'reports': reports,
        'status': status,
        'category': category,
    }
    return render(request, 'admin_panel/reports.html', context)


@admin_required
@permission_required('manage_reports')
def admin_report_action(request, report_id):
    if request.method != 'POST':
        return redirect('admin_reports')

    report = get_object_or_404(Report, id=report_id)
    action = request.POST.get('action')

    if action == 'review':
        report.status = Report.Status.REVIEWING
        report.assigned_to = request.user
        report.save(update_fields=['status', 'assigned_to'])
        messages.success(request, 'Report is now being reviewed.')
    elif action == 'resolve':
        report.status = Report.Status.RESOLVED
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.admin_notes = request.POST.get('notes', '')
        report.save(update_fields=['status', 'resolved_by', 'resolved_at', 'admin_notes'])
        log_action(request.user, AuditLog.Action.REPORT_RESOLVED, 'Report', report.id,
                   f'Resolved report: {report.target_label}')
        messages.success(request, 'Report has been resolved.')
    elif action == 'dismiss':
        report.status = Report.Status.DISMISSED
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.admin_notes = request.POST.get('notes', '')
        report.save(update_fields=['status', 'resolved_by', 'resolved_at', 'admin_notes'])
        messages.success(request, 'Report has been dismissed.')

    return redirect('admin_reports')


# ==================== AUDIT LOG ====================

@admin_required
def admin_audit_log(request):
    search = request.GET.get('search', '')
    action_filter = request.GET.get('action', '')

    logs = AuditLog.objects.select_related('actor').all()

    if action_filter:
        logs = logs.filter(action=action_filter)

    if search:
        logs = logs.filter(
            Q(description__icontains=search) |
            Q(actor__username__icontains=search) |
            Q(entity_type__icontains=search)
        )

    logs = logs.order_by('-created_at')[:200]

    context = {
        'logs': logs,
        'search': search,
        'action_filter': action_filter,
        'action_choices': AuditLog.Action.choices,
    }
    return render(request, 'admin_panel/audit_log.html', context)


# ==================== SECURITY CENTER ====================

@admin_required
@permission_required('manage_security')
def admin_security(request):
    severity = request.GET.get('severity', '')

    events = SecurityEvent.objects.select_related('user', 'resolved_by').all()

    if severity:
        events = events.filter(severity=severity)

    events = events.order_by('-created_at')[:100]

    # Stats
    total_events = SecurityEvent.objects.count()
    critical_events = SecurityEvent.objects.filter(severity=SecurityEvent.Severity.CRITICAL, is_resolved=False).count()
    high_events = SecurityEvent.objects.filter(severity=SecurityEvent.Severity.HIGH, is_resolved=False).count()
    resolved_events = SecurityEvent.objects.filter(is_resolved=True).count()

    # Suspicious accounts (users with multiple security events)
    suspicious_users = Host.objects.annotate(
        event_count=Count('security_events', filter=Q(security_events__is_resolved=False)
    )).filter(event_count__gte=2).order_by('-event_count')[:10]

    context = {
        'security_events': events,
        'total_events': total_events,
        'critical_events': critical_events,
        'high_events': high_events,
        'resolved_events': resolved_events,
        'suspicious_users': suspicious_users,
        'severity': severity,
    }
    return render(request, 'admin_panel/security.html', context)


@admin_required
@permission_required('manage_security')
def admin_security_action(request, event_id):
    if request.method != 'POST':
        return redirect('admin_security')

    sec_event = get_object_or_404(SecurityEvent, id=event_id)
    action = request.POST.get('action')

    if action == 'resolve':
        sec_event.is_resolved = True
        sec_event.resolved_by = request.user
        sec_event.resolved_at = timezone.now()
        sec_event.save(update_fields=['is_resolved', 'resolved_by', 'resolved_at'])
        log_action(request.user, AuditLog.Action.SECURITY_ACTION, 'SecurityEvent', sec_event.id,
                   f'Resolved security event: {sec_event.get_event_type_display()}')
        messages.success(request, 'Security event resolved.')
    elif action == 'lockout':
        if sec_event.user:
            sec_event.user.is_suspended = True
            sec_event.user.suspended_at = timezone.now()
            sec_event.user.suspended_by = request.user
            sec_event.user.suspension_reason = f'Auto-locked due to security event: {sec_event.get_event_type_display()}'
            sec_event.user.save(update_fields=['is_suspended', 'suspended_at', 'suspended_by', 'suspension_reason'])
            log_action(request.user, AuditLog.Action.SECURITY_ACTION, 'Host', sec_event.user.id,
                       f'Locked out user {sec_event.user.username} due to security event')
            messages.success(request, f'User {sec_event.user.username} has been locked out.')

    return redirect('admin_security')


# ==================== SUPPORT & DISPUTES ====================

@admin_required
@permission_required('manage_support')
def admin_support(request):
    status = request.GET.get('status', '')
    priority = request.GET.get('priority', '')

    tickets = SupportTicket.objects.select_related('user', 'assigned_to').all()

    if status:
        tickets = tickets.filter(status=status)

    if priority:
        tickets = tickets.filter(priority=priority)

    tickets = tickets.order_by('-created_at')[:100]

    context = {
        'tickets': tickets,
        'status': status,
        'priority': priority,
    }
    return render(request, 'admin_panel/support.html', context)


@admin_required
@permission_required('manage_support')
def admin_support_detail(request, ticket_id):
    ticket = get_object_or_404(SupportTicket.objects.select_related('user', 'assigned_to'), id=ticket_id)
    replies = ticket.replies.select_related('author').all()

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            TicketReply.objects.create(
                ticket=ticket,
                author=request.user,
                content=content,
                is_admin=True,
            )
            if ticket.status == SupportTicket.Status.OPEN:
                ticket.status = SupportTicket.Status.PENDING
                ticket.assigned_to = request.user
                ticket.save(update_fields=['status', 'assigned_to'])
            log_action(request.user, AuditLog.Action.SUPPORT_UPDATED, 'SupportTicket', ticket.id,
                       f'Replied to ticket: {ticket.subject}')
            messages.success(request, 'Reply sent.')
            return redirect('admin_support_detail', ticket_id=ticket_id)

    context = {
        'ticket': ticket,
        'replies': replies,
    }
    return render(request, 'admin_panel/support_detail.html', context)


@admin_required
@permission_required('manage_support')
def admin_support_action(request, ticket_id):
    if request.method != 'POST':
        return redirect('admin_support')

    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    action = request.POST.get('action')

    if action == 'resolve':
        ticket.status = SupportTicket.Status.RESOLVED
        ticket.save(update_fields=['status'])
        log_action(request.user, AuditLog.Action.SUPPORT_UPDATED, 'SupportTicket', ticket.id,
                   f'Resolved ticket: {ticket.subject}')
        messages.success(request, 'Ticket resolved.')
    elif action == 'close':
        ticket.status = SupportTicket.Status.CLOSED
        ticket.closed_at = timezone.now()
        ticket.save(update_fields=['status', 'closed_at'])
        messages.success(request, 'Ticket closed.')
    elif action == 'reopen':
        ticket.status = SupportTicket.Status.OPEN
        ticket.closed_at = None
        ticket.save(update_fields=['status', 'closed_at'])
        messages.success(request, 'Ticket reopened.')
    elif action == 'priority':
        ticket.priority = request.POST.get('priority', ticket.priority)
        ticket.save(update_fields=['priority'])
        messages.success(request, 'Priority updated.')
    elif action == 'assign':
        ticket.assigned_to = request.user
        ticket.save(update_fields=['assigned_to'])
        messages.success(request, 'Ticket assigned to you.')

    return redirect('admin_support_detail', ticket_id=ticket_id)


# ==================== NOTIFICATIONS ====================

@admin_required
@permission_required('manage_notifications')
def admin_notifications(request):
    notifications = PlatformNotification.objects.select_related('created_by').order_by('-created_at')[:50]

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        notification_type = request.POST.get('notification_type', PlatformNotification.Type.ANNOUNCEMENT)
        target = request.POST.get('target', PlatformNotification.Target.ALL)

        if title and message:
            notif = PlatformNotification.objects.create(
                title=title,
                message=message,
                notification_type=notification_type,
                target=target,
                created_by=request.user,
            )
            log_action(request.user, AuditLog.Action.NOTIFICATION_SENT, 'Notification', notif.id,
                       f'Sent notification: {title} to {target}')
            messages.success(request, 'Notification sent successfully.')
            return redirect('admin_notifications')

    context = {
        'notifications': notifications,
    }
    return render(request, 'admin_panel/notifications.html', context)


# ==================== MARKETPLACE OVERSIGHT ====================

@admin_required
@permission_required('manage_vendors')
def admin_marketplace(request):
    search = request.GET.get('search', '')
    vendors = Vendor.objects.select_related('user').all()

    if search:
        vendors = vendors.filter(
            Q(business_name__icontains=search) |
            Q(city__icontains=search) |
            Q(categories__icontains=search)
        )

    vendors = vendors.annotate(
        service_count=Count('services'),
        review_count=Count('reviews')
    ).order_by('-average_rating', '-total_bookings')[:50]

    categories = ServiceCategory.objects.all()
    featured = FeaturedVendor.objects.select_related('vendor').filter(is_active=True)[:20]

    context = {
        'vendors': vendors,
        'categories': categories,
        'featured': featured,
        'search': search,
    }
    return render(request, 'admin_panel/marketplace.html', context)


@admin_required
@permission_required('manage_vendors')
def admin_marketplace_category(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if name:
            cat, created = ServiceCategory.objects.get_or_create(name=name, defaults={'description': description})
            if created:
                log_action(request.user, AuditLog.Action.CATEGORY_CREATED, 'ServiceCategory', cat.id,
                           f'Created category: {name}')
                messages.success(request, f'Category "{name}" created.')
            else:
                messages.info(request, f'Category "{name}" already exists.')
        return redirect('admin_marketplace')


@admin_required
@permission_required('manage_vendors')
def admin_marketplace_feature(request):
    if request.method == 'POST':
        vendor_id = request.POST.get('vendor_id')
        priority = int(request.POST.get('priority', 0))
        vendor = get_object_or_404(Vendor, id=vendor_id)
        fv, created = FeaturedVendor.objects.get_or_create(
            vendor=vendor, defaults={'priority': priority, 'created_by': request.user}
        )
        if not created:
            fv.is_active = not fv.is_active
            fv.priority = priority
            fv.save(update_fields=['is_active', 'priority'])
        log_action(request.user, AuditLog.Action.VENDOR_FEATURED, 'Vendor', vendor.id,
                   f'Featured vendor: {vendor.business_name}')
        messages.success(request, 'Featured listing updated.')
    return redirect('admin_marketplace')


# ==================== ANALYTICS ====================

@admin_required
@permission_required('view_analytics')
def admin_analytics(request):
    now = timezone.now()

    # User growth over 12 months
    months = []
    hosts_growth = []
    vendors_growth = []
    events_growth = []
    guests_growth = []
    bookings_trend = []

    for i in range(11, -1, -1):
        month_start = now.replace(day=1) - timedelta(days=30 * i)
        month_end = month_start + timedelta(days=30)
        months.append(month_start.strftime('%b %Y'))
        hosts_growth.append(Host.objects.filter(created_at__lt=month_end, vendor_profile__isnull=True).count())
        vendors_growth.append(Vendor.objects.filter(created_at__lt=month_end).count())
        events_growth.append(Event.objects.filter(created_at__lt=month_end).count())
        guests_growth.append(Guest.objects.filter(registered_at__lt=month_end).count())
        bookings_trend.append(Booking.objects.filter(created_at__lt=month_end).count())

    # Category distribution
    category_data = {}
    for event in Event.objects.all():
        cat = event.get_category_display()
        category_data[cat] = category_data.get(cat, 0) + 1

    # Vendor category distribution
    vendor_cat_data = {}
    for vendor in Vendor.objects.all():
        for cat in vendor.category_list:
            vendor_cat_data[cat] = vendor_cat_data.get(cat, 0) + 1

    # Geographic distribution
    geo_data = {}
    for vendor in Vendor.objects.exclude(city=''):
        geo_data[vendor.city] = geo_data.get(vendor.city, 0) + 1

    # Booking status distribution
    booking_status_data = {}
    for choice in Booking.Status.choices:
        booking_status_data[choice[1]] = Booking.objects.filter(status=choice[0]).count()

    # Attendance metrics
    total_guests = Guest.objects.count()
    total_checked_in = Guest.objects.filter(checked_in=True).count()
    attendance_rate = round((total_checked_in / total_guests * 100), 1) if total_guests > 0 else 0

    # Revenue trends (booking values)
    completed_bookings = Booking.objects.filter(status=Booking.Status.COMPLETED).count()
    total_booking_value = sum(b.agreed_price for b in Booking.objects.filter(status=Booking.Status.COMPLETED))

    context = {
        'months_json': json.dumps(months),
        'hosts_growth_json': json.dumps(hosts_growth),
        'vendors_growth_json': json.dumps(vendors_growth),
        'events_growth_json': json.dumps(events_growth),
        'guests_growth_json': json.dumps(guests_growth),
        'bookings_trend_json': json.dumps(bookings_trend),
        'category_data_json': json.dumps(category_data),
        'vendor_cat_data_json': json.dumps(vendor_cat_data),
        'geo_data_json': json.dumps(geo_data),
        'booking_status_json': json.dumps(booking_status_data),
        'total_guests': total_guests,
        'total_checked_in': total_checked_in,
        'attendance_rate': attendance_rate,
        'completed_bookings': completed_bookings,
        'total_booking_value': total_booking_value,
    }
    return render(request, 'admin_panel/analytics.html', context)


# ==================== PLATFORM SETTINGS ====================

@admin_required
@permission_required('manage_settings')
def admin_settings(request):
    settings_obj = PlatformSettings.get_settings()

    if request.method == 'POST':
        settings_obj.platform_name = request.POST.get('platform_name', settings_obj.platform_name)
        settings_obj.support_email = request.POST.get('support_email', settings_obj.support_email)
        settings_obj.maintenance_mode = request.POST.get('maintenance_mode') == 'on'
        settings_obj.maintenance_message = request.POST.get('maintenance_message', settings_obj.maintenance_message)
        settings_obj.max_events_per_host = int(request.POST.get('max_events_per_host', 50))
        settings_obj.max_guests_per_event = int(request.POST.get('max_guests_per_event', 10000))
        settings_obj.vendor_approval_required = request.POST.get('vendor_approval_required') == 'on'
        settings_obj.host_approval_required = request.POST.get('host_approval_required') == 'on'
        settings_obj.commission_rate = float(request.POST.get('commission_rate', 5.00))
        settings_obj.enable_marketplace = request.POST.get('enable_marketplace') == 'on'
        settings_obj.enable_vendor_registration = request.POST.get('enable_vendor_registration') == 'on'
        settings_obj.updated_by = request.user
        settings_obj.save()
        log_action(request.user, AuditLog.Action.SETTINGS_CHANGED, 'PlatformSettings', settings_obj.id,
                   'Updated platform settings')
        messages.success(request, 'Platform settings updated.')
        return redirect('admin_settings')

    context = {
        'settings': settings_obj,
    }
    return render(request, 'admin_panel/settings.html', context)


# ==================== STAFF MANAGEMENT ====================

@admin_required
@permission_required('manage_staff')
def admin_staff(request):
    search = request.GET.get('search', '')
    staff = Host.objects.filter(admin_role__isnull=False).select_related('admin_role')

    if search:
        staff = staff.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search)
        )

    staff = staff.order_by('-admin_role__created_at')

    all_users = Host.objects.filter(admin_role__isnull=True, is_staff=False, is_superuser=False).order_by('-created_at')[:50]

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role = request.POST.get('role')
        user = get_object_or_404(Host, id=user_id)
        if user.id == request.user.id and role != AdminRole.Role.SUPER_ADMIN:
            messages.error(request, 'You cannot change your own role.')
            return redirect('admin_staff')

        admin_role, created = AdminRole.objects.get_or_create(
            user=user, defaults={'role': role, 'assigned_by': request.user}
        )
        if not created:
            admin_role.role = role
            admin_role.assigned_by = request.user
            admin_role.save(update_fields=['role', 'assigned_by'])

        user.is_staff = True
        user.save(update_fields=['is_staff'])

        log_action(request.user, AuditLog.Action.ADMIN_ASSIGNED, 'AdminRole', admin_role.id,
                   f'Assigned {user.username} as {role}')
        messages.success(request, f'{user.username} assigned as {admin_role.get_role_display()}.')
        return redirect('admin_staff')

    context = {
        'staff': staff,
        'all_users': all_users,
        'search': search,
    }
    return render(request, 'admin_panel/staff.html', context)


@admin_required
@permission_required('manage_staff')
def admin_staff_remove(request, user_id):
    if request.method != 'POST':
        return redirect('admin_staff')

    user = get_object_or_404(Host, id=user_id)
    if user.id == request.user.id:
        messages.error(request, 'You cannot remove your own admin role.')
        return redirect('admin_staff')

    if hasattr(user, 'admin_role'):
        user.admin_role.delete()
        user.is_staff = False
        user.save(update_fields=['is_staff'])
        log_action(request.user, AuditLog.Action.ADMIN_ASSIGNED, 'AdminRole', user_id,
                   f'Removed admin role from {user.username}')
        messages.success(request, f'Admin role removed from {user.username}.')

    return redirect('admin_staff')


# ==================== PAYMENTS DASHBOARD ====================

@admin_required
@permission_required('manage_payments')
def admin_payments_dashboard(request):
    """
    Daily-use finance overview: revenue across time windows, payment status
    counts, top-earning events, and recent activity.

    Production notes:
    - All sums computed in the DB via aggregate()
    - Commission rate safely coerced from float settings to Decimal
    - No N+1: recent_paid and recent_pending use select_related
    - top_events is a bounded aggregate ([:10])
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # ---- Revenue across time windows ----
    paid_guests = Guest.objects.filter(payment_status='paid', amount_paid__gt=0)

    def _sum_window(qs):
        """Helper: return Decimal sum or 0.00 — never None."""
        return qs.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

    total_revenue = _sum_window(paid_guests)
    revenue_today = _sum_window(paid_guests.filter(registered_at__gte=today_start))
    revenue_week  = _sum_window(paid_guests.filter(registered_at__gte=week_start))
    revenue_month = _sum_window(paid_guests.filter(registered_at__gte=month_start))

    # ---- Guest counts by payment status ----
    paid_count = paid_guests.count()
    pending_count = Guest.objects.filter(payment_status='pending').count()
    failed_count = Guest.objects.filter(payment_status='failed').count()
    refunded_count = Guest.objects.filter(payment_status='refunded').count()

    # ---- Recent successful transactions ----
    recent_paid = (
        Guest.objects
        .filter(payment_status='paid', amount_paid__gt=0)
        .select_related('event', 'event__host')
        .only(
            'id', 'full_name', 'email', 'amount_paid',
            'registered_at', 'payment_reference',
            'event__id', 'event__name', 'event__host__username',
        )
        .order_by('-registered_at')[:15]
    )

    # ---- Recent pending (needs follow-up) ----
    recent_pending = (
        Guest.objects
        .filter(payment_status='pending')
        .select_related('event')
        .only(
            'id', 'full_name', 'email', 'amount_paid',
            'registered_at', 'payment_reference',
            'event__id', 'event__name',
        )
        .order_by('-registered_at')[:10]
    )

    # ---- Top-earning events (bounded) ----
    top_events = (
        Guest.objects
        .filter(payment_status='paid', amount_paid__gt=0)
        .values(
            'event__id',
            'event__name',
            'event__host__username',
            'event__date',
        )
        .annotate(
            revenue=Sum('amount_paid'),
            guests=Count('id', distinct=True),
        )
        .order_by('-revenue')[:10]
    )

    # ---- Commission rate: safe coercion from float to Decimal ----
    commission_rate = Decimal('0.05')  # default 5%
    try:
        settings_obj = PlatformSettings.get_settings()
        raw = settings_obj.commission_rate
        if raw is not None:
            # Coerce to Decimal via string to avoid float precision loss.
            # e.g. float 5.0 -> Decimal('5.0') -> Decimal('0.05')
            pct = Decimal(str(raw))
            commission_rate = (pct / Decimal('100')).quantize(Decimal('0.0001'))
    except Exception as exc:
        logger.warning('Failed to load commission rate, using default 5%: %s', exc)

    platform_commission = (total_revenue * commission_rate).quantize(Decimal('0.01'))
    host_earnings = (total_revenue - platform_commission).quantize(Decimal('0.01'))

    context = {
        'total_revenue': total_revenue,
        'revenue_today': revenue_today,
        'revenue_week': revenue_week,
        'revenue_month': revenue_month,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'failed_count': failed_count,
        'refunded_count': refunded_count,
        'recent_paid': recent_paid,
        'recent_pending': recent_pending,
        'top_events': top_events,
        'platform_commission': platform_commission,
        'host_earnings': host_earnings,
        'commission_rate_pct': (commission_rate * Decimal('100')).quantize(Decimal('0.01')),
    }
    return render(request, 'admin_panel/payments_dashboard.html', context)

# ==================== TRANSACTIONS ====================

@admin_required
@permission_required('manage_payments')
def admin_transactions(request):
    """Searchable list of every guest payment and its status."""

    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    event_filter = request.GET.get('event', '').strip()

    guests = Guest.objects.select_related('event', 'event__host').all()

    if status_filter:
        guests = guests.filter(payment_status=status_filter)

    if event_filter:
        guests = guests.filter(event_id=event_filter)

    if search:
        guests = guests.filter(
            Q(full_name__icontains=search) |
            Q(email__icontains=search) |
            Q(payment_reference__icontains=search) |
            Q(event__name__icontains=search) |
            Q(ticket_code__icontains=search)
        )

    guests = guests.order_by('-registered_at')[:200]

    # Aggregate totals for the header
    paid_set = Guest.objects.filter(payment_status='paid')

    total_revenue = paid_set.aggregate(
        total=Sum('amount_paid')
    )['total'] or Decimal('0.00')

    paid_count = paid_set.count()
    pending_count = Guest.objects.filter(payment_status='pending').count()
    failed_count = Guest.objects.filter(payment_status='failed').count()

    # For the event filter dropdown — only events that have guests
    event_choices = (
        Event.objects
        .filter(guests__isnull=False)
        .distinct()
        .order_by('-date')[:100]
    )

    context = {
        'transactions': guests,
        'search': search,
        'status_filter': status_filter,
        'event_filter': event_filter,
        'event_choices': event_choices,
        'total_revenue': total_revenue,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'failed_count': failed_count,
    }
    return render(request, 'admin_panel/transactions.html', context)


# ==================== HOST PAYOUTS ====================

@admin_required
@permission_required('manage_payments')
def admin_host_payouts(request):
    """Hosts and their connected Paystack subaccounts."""

    # Commission rate — from PlatformSettings if available, else 5%
    commission_rate = Decimal('0.05')
    try:
        settings_obj = PlatformSettings.get_settings()
        commission_rate = (settings_obj.commission_rate or Decimal('5.00')) / Decimal('100')
    except Exception:
        pass

    # Hosts with a connected bank account
    connected = (
        HostPaymentAccount.objects
        .select_related('host')
        .filter(is_verified=True)
        .order_by('-created_at')
    )

    connected_data = []
    for account in connected:
        # Gross revenue from this host's paid guests
        gross = (
            Guest.objects
            .filter(
                event__host=account.host,
                payment_status='paid',
                amount_paid__gt=0,
            )
            .aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
        )

        # Platform commission on that gross
        platform_fee = (gross * commission_rate).quantize(Decimal('0.01'))

        # What the host actually receives
        net = (gross - platform_fee).quantize(Decimal('0.01'))

        # Number of paid events for this host
        paid_events = (
            Guest.objects
            .filter(event__host=account.host, payment_status='paid', amount_paid__gt=0)
            .values('event_id')
            .distinct()
            .count()
        )

        connected_data.append({
            'host': account.host,
            'bank_name': account.bank_name,
            'account_number': account.account_number,
            'account_name': account.account_name,
            'subaccount_code': account.subaccount_code,
            'connected_at': account.created_at,
            'gross_earnings': gross,
            'platform_fee': platform_fee,
            'net_earnings': net,
            'paid_events_count': paid_events,
        })

    # Hosts who have NOT connected — the ones you may want to nudge
    unconnected_hosts = (
        Host.objects
        .filter(
            vendor_profile__isnull=True,
            is_superuser=False,
            is_staff=False,
            is_suspended=False,
            payment_account__isnull=True,
        )
        .order_by('-created_at')[:50]
    )

    # Global totals
    total_gross = sum(d['gross_earnings'] for d in connected_data) if connected_data else Decimal('0.00')
    total_platform = sum(d['platform_fee'] for d in connected_data) if connected_data else Decimal('0.00')
    total_net = sum(d['net_earnings'] for d in connected_data) if connected_data else Decimal('0.00')

    context = {
        'connected_hosts': connected_data,
        'unconnected_hosts': unconnected_hosts,
        'commission_rate': (commission_rate * 100).quantize(Decimal('0.01')),
        'total_gross': total_gross,
        'total_platform': total_platform,
        'total_net': total_net,
        'connected_count': len(connected_data),
        'unconnected_count': unconnected_hosts.count() if hasattr(unconnected_hosts, 'count') else len(unconnected_hosts),
    }
    return render(request, 'admin_panel/host_payouts.html', context)

# ==================== VENDOR SUBSCRIPTIONS ====================


@admin_required
@permission_required('manage_payments')
def admin_subscriptions(request):
    """
    Vendor subscription overview.

    Production notes:
    - Uses select_related for vendor + plan (avoids N+1)
    - Paginates at 50/page
    - MRR computed in the database, not Python
    - Tolerates a missing SubscriptionPlan.monthly_price field gracefully
    """
    from vendors.models import VendorSubscription, SubscriptionPlan

    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    plan_filter = request.GET.get('plan', '').strip()
    page_number = request.GET.get('page', 1)

    # ---- Base queryset: always select_related ----
    subs_qs = (
        VendorSubscription.objects
        .select_related('vendor', 'vendor__user', 'plan')
        .all()
    )

    if status_filter:
        subs_qs = subs_qs.filter(status=status_filter)

    if plan_filter:
        subs_qs = subs_qs.filter(plan_id=plan_filter)

    if search:
        subs_qs = subs_qs.filter(
            Q(vendor__business_name__icontains=search) |
            Q(vendor__user__email__icontains=search) |
            Q(vendor__user__username__icontains=search)
        )

    subs_qs = subs_qs.order_by('-created_at')

    # ---- Pagination (production: never slice manually) ----
    paginator = Paginator(subs_qs, 50)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # ---- Status counts (single query, all statuses) ----
    status_counts_raw = (
        VendorSubscription.objects
        .values('status')
        .annotate(count=Count('id'))
    )
    status_counts = {row['status']: row['count'] for row in status_counts_raw}

    trialing = status_counts.get(VendorSubscription.Status.TRIALING, 0)
    active = status_counts.get(VendorSubscription.Status.ACTIVE, 0)
    past_due = status_counts.get(VendorSubscription.Status.PAST_DUE, 0)
    cancelled = status_counts.get(VendorSubscription.Status.CANCELLED, 0)
    free = status_counts.get(VendorSubscription.Status.FREE, 0)

    # ---- MRR: database-side aggregation ----
    # Guard against plan.monthly_price being null
    mrr = (
        VendorSubscription.objects
        .filter(
            status=VendorSubscription.Status.ACTIVE,
            plan__monthly_price__gt=0,
        )
        .aggregate(
            total=Coalesce(
                Sum('plan__monthly_price'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )['total']
    )

    # ---- ARR (annualized) ----
    arr = (mrr * Decimal('12')).quantize(Decimal('0.01'))

    # ---- Plans for the filter dropdown ----
    plans = (
        SubscriptionPlan.objects
        .filter(is_active=True)
        .order_by('monthly_price')
    )

    # ---- Plan distribution (how many vendors on each plan) ----
    plan_distribution = (
        VendorSubscription.objects
        .filter(status__in=[
            VendorSubscription.Status.ACTIVE,
            VendorSubscription.Status.TRIALING,
        ])
        .values('plan__name', 'plan__monthly_price')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    context = {
        'subscriptions': page_obj,   # template iterates page_obj
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'status_filter': status_filter,
        'plan_filter': plan_filter,
        'trialing_count': trialing,
        'active_count': active,
        'past_due_count': past_due,
        'cancelled_count': cancelled,
        'free_count': free,
        'total_count': paginator.count,
        'mrr': mrr,
        'arr': arr,
        'plans': plans,
        'plan_distribution': plan_distribution,
    }
    return render(request, 'admin_panel/subscriptions.html', context)