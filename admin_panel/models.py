import uuid
from django.db import models
from django.conf import settings


class AdminRole(models.Model):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        OPERATIONS = 'operations', 'Operations Admin'
        SUPPORT = 'support', 'Support Admin'
        FINANCE = 'finance', 'Finance Admin'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_role')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OPERATIONS)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_admin_roles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.get_role_display()}"

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_operations(self):
        return self.role == self.Role.OPERATIONS

    @property
    def is_support(self):
        return self.role == self.Role.SUPPORT

    @property
    def is_finance(self):
        return self.role == self.Role.FINANCE

    def can(self, permission):
        return permission in self.permissions

    @property
    def permissions(self):
        if self.is_super_admin:
            return {'manage_users', 'manage_events', 'manage_vendors', 'manage_payments',
                    'manage_settings', 'manage_staff', 'manage_reports', 'view_analytics',
                    'manage_security', 'manage_notifications', 'manage_support'}
        if self.is_operations:
            return {'manage_users', 'manage_events', 'manage_vendors', 'manage_reports',
                    'view_analytics', 'manage_security'}
        if self.is_support:
            return {'manage_users', 'manage_reports', 'manage_support'}
        if self.is_finance:
            return {'view_analytics', 'manage_payments'}
        return set()


class AuditLog(models.Model):
    class Action(models.TextChoices):
        VENDOR_APPROVED = 'vendor_approved', 'Vendor Approved'
        VENDOR_REJECTED = 'vendor_rejected', 'Vendor Rejected'
        VENDOR_SUSPENDED = 'vendor_suspended', 'Vendor Suspended'
        VENDOR_BADGE = 'vendor_badge', 'Vendor Badge Changed'
        HOST_VERIFIED = 'host_verified', 'Host Verified'
        HOST_SUSPENDED = 'host_suspended', 'Host Suspended'
        HOST_ACTIVATED = 'host_activated', 'Host Activated'
        EVENT_SUSPENDED = 'event_suspended', 'Event Suspended'
        EVENT_ARCHIVED = 'event_archived', 'Event Archived'
        EVENT_REVIEWED = 'event_reviewed', 'Event Reviewed'
        REPORT_RESOLVED = 'report_resolved', 'Report Resolved'
        SUPPORT_UPDATED = 'support_updated', 'Support Ticket Updated'
        NOTIFICATION_SENT = 'notification_sent', 'Notification Sent'
        SETTINGS_CHANGED = 'settings_changed', 'Platform Settings Changed'
        ADMIN_ASSIGNED = 'admin_assigned', 'Admin Role Assigned'
        USER_DELETED = 'user_deleted', 'User Deleted'
        CATEGORY_CREATED = 'category_created', 'Category Created'
        VENDOR_FEATURED = 'vendor_featured', 'Vendor Featured'
        SECURITY_ACTION = 'security_action', 'Security Action Taken'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='admin_audit_logs')
    action = models.CharField(max_length=30, choices=Action.choices)
    entity_type = models.CharField(max_length=50, blank=True, default='')
    entity_id = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} by {self.actor} at {self.created_at}"


class Report(models.Model):
    class Category(models.TextChoices):
        FAKE_VENDOR = 'fake_vendor', 'Fake Vendor'
        FAKE_EVENT = 'fake_event', 'Fake Event'
        HARASSMENT = 'harassment', 'Harassment'
        SCAM = 'scam', 'Scam'
        INAPPROPRIATE = 'inappropriate', 'Inappropriate Content'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        REVIEWING = 'reviewing', 'Reviewing'
        RESOLVED = 'resolved', 'Resolved'
        DISMISSED = 'dismissed', 'Dismissed'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='filed_reports')
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    target_type = models.CharField(max_length=50, blank=True, default='')
    target_id = models.CharField(max_length=100, blank=True, default='')
    target_label = models.CharField(max_length=300, blank=True, default='')
    reason = models.TextField(blank=True, default='')
    admin_notes = models.TextField(blank=True, default='')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_reports')
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_reports')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_category_display()} - {self.target_label}"


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        PENDING = 'pending', 'Pending'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='support_tickets')
    subject = models.CharField(max_length=300)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.subject}"


class TicketReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply on {self.ticket.subject} by {self.author}"


class PlatformNotification(models.Model):
    class Target(models.TextChoices):
        ALL = 'all', 'All Users'
        HOSTS = 'hosts', 'Hosts Only'
        VENDORS = 'vendors', 'Vendors Only'
        STAFF = 'staff', 'Staff Only'

    class Type(models.TextChoices):
        ANNOUNCEMENT = 'announcement', 'Announcement'
        MAINTENANCE = 'maintenance', 'Maintenance Alert'
        UPDATE = 'update', 'Product Update'
        WARNING = 'warning', 'Warning'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=Type.choices, default=Type.ANNOUNCEMENT)
    target = models.CharField(max_length=20, choices=Target.choices, default=Target.ALL)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class PlatformSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    platform_name = models.CharField(max_length=200, default='EventzUp')
    support_email = models.EmailField(default='support@eventzup.com')
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True, default='We are currently performing maintenance. Please check back soon.')
    max_events_per_host = models.PositiveIntegerField(default=50)
    max_guests_per_event = models.PositiveIntegerField(default=10000)
    vendor_approval_required = models.BooleanField(default=True)
    host_approval_required = models.BooleanField(default=False)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    enable_marketplace = models.BooleanField(default=True)
    enable_vendor_registration = models.BooleanField(default=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Platform Settings'
        verbose_name_plural = 'Platform Settings'

    def __str__(self):
        return self.platform_name

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk='00000000-0000-0000-0000-000000000001', defaults={})
        return obj


class ServiceCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class FeaturedVendor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='featured_listings')
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"Featured: {self.vendor.business_name}"


class SecurityEvent(models.Model):
    class Type(models.TextChoices):
        FAILED_LOGIN = 'failed_login', 'Failed Login'
        EXCESSIVE_REGISTRATION = 'excessive_registration', 'Excessive Registration'
        SUSPICIOUS_ACTIVITY = 'suspicious_activity', 'Suspicious Activity'
        RATE_LIMIT_HIT = 'rate_limit', 'Rate Limit Hit'
        ACCOUNT_LOCKOUT = 'account_lockout', 'Account Lockout'

    class Severity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=30, choices=Type.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.LOW)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='security_events')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    description = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_security_events')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.get_severity_display()}"
