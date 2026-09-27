from core.models import Host
from vendors.models import Vendor, VendorSubscription
from .models import Report, SupportTicket, SecurityEvent
from guest.models import Guest
from django.core.cache import cache

def admin_sidebar_context(request):
    """Provide sidebar badge counts to all admin templates."""
    if not hasattr(request.user, 'admin_role'):
        return {}

    cache_key = 'admin_sidebar_counts'
    counts = cache.get(cache_key)

    if counts is None:
        counts = {
            'pending_host_verifications': Host.objects.filter(
                verification_level=0, is_suspended=False, vendor_profile__isnull=True
            ).exclude(is_superuser=True).count(),

            'pending_vendor_verifications': Vendor.objects.filter(
                verification_status=Vendor.VerificationStatus.PENDING
            ).count(),

            'pending_reports': Report.objects.filter(
                status__in=[Report.Status.PENDING, Report.Status.REVIEWING]
            ).count(),

            'critical_reports': Report.objects.filter(
                status__in=[Report.Status.PENDING, Report.Status.REVIEWING],
                priority__in=[Report.Priority.HIGH, Report.Priority.CRITICAL],
            ).count(),

            'open_tickets': SupportTicket.objects.filter(
                status__in=[SupportTicket.Status.OPEN, SupportTicket.Status.PENDING]
            ).count(),

            'security_events': SecurityEvent.objects.filter(is_resolved=False).count(),

            'pending_payments_count': Guest.objects.filter(payment_status='pending').count(),

            'past_due_subscriptions_count': VendorSubscription.objects.filter(
                status=VendorSubscription.Status.PAST_DUE
            ).count(),
        }
        cache.set(cache_key, counts, timeout=60)  # 60 seconds

    return counts