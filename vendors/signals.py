# vendors/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import Vendor, VendorSubscription, SubscriptionPlan


@receiver(post_save, sender=Vendor)
def create_vendor_subscription(sender, instance, created, **kwargs):
    """When a Vendor is created, automatically give them a free trial."""
    if not created:
        return
    
    # Skip if a subscription already exists (e.g., created manually in admin)
    if hasattr(instance, 'subscription'):
        return
    
    trial_days = getattr(settings, 'VENDOR_TRIAL_DAYS', 30)
    pro_plan = SubscriptionPlan.objects.filter(name='Pro').first()
    
    if pro_plan:
        VendorSubscription.objects.create(
            vendor=instance,
            plan=pro_plan,
            status=VendorSubscription.Status.TRIALING,
            trial_start_at=timezone.now(),
            trial_end_at=timezone.now() + timedelta(days=trial_days),
        )
    else:
        VendorSubscription.objects.create(
            vendor=instance,
            status=VendorSubscription.Status.FREE,
        )