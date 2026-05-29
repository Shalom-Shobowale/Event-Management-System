import uuid
from django.db import models
from django.conf import settings
from event.models import Event
from vendors.models import Vendor, Service


class QuoteRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        OPEN = 'open', 'Open for Proposals'
        CLOSED = 'closed', 'Closed'
        AWARDED = 'awarded', 'Awarded'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='quote_requests')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    category = models.CharField(max_length=50)
    description = models.TextField()
    budget_min = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    required_date = models.DateField()
    location = models.CharField(max_length=500, blank=True, default='')
    guest_count = models.PositiveIntegerField(default=0)
    special_requirements = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    deadline = models.DateTimeField(null=True, blank=True)
    is_urgent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"RFQ: {self.title} for {self.event.name}"


class Proposal(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'review', 'Under Review'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quote_request = models.ForeignKey(QuoteRequest, on_delete=models.CASCADE, related_name='proposals')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='proposals')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    cover_letter = models.TextField()
    proposed_price = models.DecimalField(max_digits=12, decimal_places=2)
    includes = models.TextField(blank=True, default='')
    terms = models.TextField(blank=True, default='')
    estimated_duration_hours = models.PositiveIntegerField(default=4)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['proposed_price']

    def __str__(self):
        return f"Proposal from {self.vendor.business_name} for {self.quote_request.title}"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Confirmation'
        CONFIRMED = 'confirmed', 'Confirmed'
        IN_PROGRESS = 'progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True)
    proposal = models.ForeignKey(Proposal, on_delete=models.SET_NULL, null=True, blank=True)
    service_name = models.CharField(max_length=300)
    description = models.TextField(blank=True, default='')
    agreed_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    vendor_notes = models.TextField(blank=True, default='')
    host_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.vendor.business_name} - {self.service_name} for {self.event.name}"

    def confirm(self):
        from django.utils import timezone
        self.status = self.Status.CONFIRMED
        self.save()

    def complete(self):
        from django.utils import timezone
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save()
        # Update vendor stats
        self.vendor.total_bookings += 1
        self.vendor.save(update_fields=['total_bookings'])
