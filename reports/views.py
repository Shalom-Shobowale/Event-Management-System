import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from admin_panel.models import Report
from admin_panel.services import log_action
from admin_panel.models import AuditLog

from .forms import ReportForm, SUPPORTED_TARGETS

logger = logging.getLogger(__name__)

# Rate limit — max 3 reports per rolling 24h per user.
RATE_LIMIT_PER_DAY = 3
RATE_LIMIT_WINDOW = timedelta(hours=24)

# Description limits, mirrored from the form for error messages.
MAX_DESCRIPTION_LENGTH = 2000


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------
# Given a target_type and target_id, verify the thing exists and return
# a canonical label. If the target doesn't exist, we reject the report
# (prevents spam like target_id="99999" that doesn't point anywhere).
# ---------------------------------------------------------------------------

def _resolve_target(target_type, target_id):
    """
    Return (exists: bool, canonical_label: str).
    Imports are local to avoid circular imports at module load.
    """
    try:
        if target_type == 'vendor':
            from vendors.models import Vendor
            obj = Vendor.objects.filter(pk=target_id).first()
            return (obj is not None, obj.business_name if obj else '')

        if target_type == 'event':
            from event.models import Event
            obj = Event.objects.filter(pk=target_id).first()
            return (obj is not None, obj.name if obj else '')

        if target_type == 'host':
            from core.models import Host
            obj = Host.objects.filter(pk=target_id).first()
            if obj:
                return (True, obj.get_full_name() or obj.username)
            return (False, '')

        if target_type == 'review':
            from vendors.models import VendorReview
            obj = VendorReview.objects.filter(pk=target_id).first()
            return (obj is not None, f'Review on {obj.vendor.business_name}' if obj else '')

        if target_type == 'message':
            # Adjust import path to your messaging app if different
            from collaboration.models import Message  # noqa
            obj = Message.objects.filter(pk=target_id).first()
            return (obj is not None, 'Conversation message' if obj else '')

        if target_type == 'booking':
            from bookings.models import Booking
            obj = Booking.objects.filter(pk=target_id).first()
            return (obj is not None, f'Booking #{str(obj.id)[:8]}' if obj else '')

    except Exception as exc:
        logger.warning('Target resolution failed for %s/%s: %s', target_type, target_id, exc)

    return (False, '')


# ---------------------------------------------------------------------------
# Rate limiting + duplicate guard
# ---------------------------------------------------------------------------

def _recent_report_count(user):
    """How many reports has this user filed in the last 24h?"""
    cutoff = timezone.now() - RATE_LIMIT_WINDOW
    return Report.objects.filter(reporter=user, created_at__gte=cutoff).count()


def _already_reported(user, target_type, target_id):
    """
    True if the user already has a pending or reviewing report on this
    exact target. Resolved/dismissed reports don't block new ones.
    """
    return Report.objects.filter(
        reporter=user,
        target_type=target_type,
        target_id=str(target_id),
        status__in=[Report.Status.PENDING, Report.Status.REVIEWING],
    ).exists()


# ---------------------------------------------------------------------------
# The view
# ---------------------------------------------------------------------------

@login_required
@require_POST
def create_report(request):
    """
    POST-only endpoint to file a report.

    Accepts both:
    - Standard form POST (redirects back with a flash message)
    - XHR/fetch POST (returns JSON — used by the modal)
    """
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.headers.get('Accept', '').startswith('application/json')
    )

    def fail(msg, status=400):
        if is_ajax:
            return JsonResponse({'ok': False, 'error': msg}, status=status)
        messages.error(request, msg)
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # ---- 1. Rate limit ----
    if _recent_report_count(request.user) >= RATE_LIMIT_PER_DAY:
        return fail(
            f'You have reached the daily limit of {RATE_LIMIT_PER_DAY} reports. '
            'Please try again later.'
        )

    # ---- 2. Form validation ----
    form = ReportForm(request.POST)
    if not form.is_valid():
        # Return the first error in a human-readable way
        first_error = next(iter(form.errors.values()))[0]
        return fail(str(first_error))

    data = form.cleaned_data
    target_type = data['target_type']
    target_id = str(data['target_id'])
    category = data['category']
    reason = data['reason']

    # ---- 3. Target must exist ----
    exists, canonical_label = _resolve_target(target_type, target_id)
    if not exists:
        return fail('The item you are trying to report no longer exists.')

    # ---- 4. Can't report yourself ----
    if target_type == 'host' and str(request.user.pk) == target_id:
        return fail('You cannot report yourself.')

    if target_type == 'vendor':
        # If the reporter is the vendor's own user, block self-report
        from vendors.models import Vendor
        vendor = Vendor.objects.filter(pk=target_id).select_related('user').first()
        if vendor and vendor.user_id == request.user.pk:
            return fail('You cannot report your own vendor profile.')

    # ---- 5. Duplicate guard ----
    if _already_reported(request.user, target_type, target_id):
        return fail(
            'You already have an open report on this item. '
            'Our team is reviewing it.'
        )

    # ---- 6. Create the report ----
    try:
        report = Report.objects.create(
            reporter=request.user,
            category=category,
            priority=ReportForm.priority_for(category),
            status=Report.Status.PENDING,
            target_type=target_type,
            target_id=target_id,
            target_label=canonical_label,
            reason=reason,
        )
    except Exception as exc:
        logger.exception('Failed to create Report: %s', exc)
        return fail('Something went wrong saving your report. Please try again.', status=500)

    # ---- 7. Audit trail ----
    try:
        log_action(
            actor=request.user,
            action=AuditLog.Action.REPORT_RESOLVED,  # reuse the closest existing action
            entity_type='Report',
            entity_id=str(report.id),
            description=f'Filed {target_type} report on "{canonical_label}" — {category}',
        )
    except Exception as exc:
        # Audit log failure must not break the user's submission
        logger.warning('Audit log failed for report %s: %s', report.id, exc)

    # ---- 8. Success ----
    success_msg = "Report received. We'll review it shortly."

    if is_ajax:
        return JsonResponse({
            'ok': True,
            'message': success_msg,
            'report_id': str(report.id),
        })

    messages.success(request, success_msg)
    return redirect(request.META.get('HTTP_REFERER', '/'))


# ---------------------------------------------------------------------------
# Template tag helper: render the button partial with the right categories
# ---------------------------------------------------------------------------

def report_context(target_type):
    """
    Returns the context needed to render the report button/modal for a
    given target type. Used by the _report_button.html partial.
    """
    return {
        'report_target_type': target_type,
        'report_categories': ReportForm.labels_for(target_type),
        'report_rate_limit': RATE_LIMIT_PER_DAY,
    }