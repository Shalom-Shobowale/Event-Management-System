import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
import random
import string


def _generate_code(length=6):
    return ''.join(random.choices(string.digits, k=length))


def _generate_token(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


class EmailVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_verifications')
    code = models.CharField(max_length=6, default=_generate_code)
    token = models.CharField(max_length=32, default=_generate_token, unique=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def create_for(cls, user):
        from datetime import timedelta
        existing = cls.objects.filter(user=user, is_verified=False, expires_at__gt=timezone.now())
        if existing.exists():
            return existing.first()
        return cls.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=24),
        )

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class PhoneVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='phone_verifications')
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=6, default=_generate_code)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def create_for(cls, user, phone):
        from datetime import timedelta
        return cls.objects.create(
            user=user,
            phone=phone,
            expires_at=timezone.now() + timedelta(hours=1),
        )

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class VendorDocument(models.Model):
    class DocType(models.TextChoices):
        BUSINESS_LICENSE = 'license', 'Business License'
        ID_PROOF = 'id', 'ID Proof'
        INSURANCE = 'insurance', 'Insurance Certificate'
        CERTIFICATION = 'cert', 'Professional Certification'
        OTHER = 'other', 'Other Document'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=20, choices=DocType.choices, default=DocType.OTHER)
    file = models.FileField(upload_to='vendor_docs/')
    name = models.CharField(max_length=300)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class UserNotification(models.Model):
    class Type(models.TextChoices):
        EVENT_REMINDER = 'event_reminder', 'Event Reminder'
        BOOKING_UPDATE = 'booking_update', 'Booking Update'
        VERIFICATION = 'verification', 'Verification Update'
        SUPPORT = 'support', 'Support Update'
        ANNOUNCEMENT = 'announcement', 'Platform Announcement'
        SYSTEM = 'system', 'System Message'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM)
    title = models.CharField(max_length=300)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    link = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def notify(cls, user, title, message, notification_type=Type.SYSTEM, link=''):
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
        )

    def mark_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
