from django.contrib.auth.models import AbstractUser
from django.db import models


class Host(AbstractUser):
    phone = models.CharField(max_length=20, blank=True, default='')
    organization = models.CharField(max_length=200, blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, default='')
    email_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Verification & Trust
    verification_level = models.PositiveIntegerField(default=0)
    phone_verified = models.BooleanField(default=False)

    # Suspension
    is_suspended = models.BooleanField(default=False)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='suspended_users')
    suspension_reason = models.TextField(blank=True, default='')

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def verification_label(self):
        labels = {0: 'Unverified', 1: 'Email Verified', 2: 'Phone Verified', 3: 'Trusted Host'}
        return labels.get(self.verification_level, 'Unverified')

    @property
    def is_vendor(self):
        return hasattr(self, 'vendor_profile')

    @property
    def is_admin_staff(self):
        return hasattr(self, 'admin_role')

    @property
    def host_subaccount_code(self):
        account = getattr(self, 'payment_account', None)
        return account.subaccount_code if account else ''
