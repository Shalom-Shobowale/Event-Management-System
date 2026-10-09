from decimal import Decimal
import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify


class EventCategory(models.TextChoices):
    CONFERENCE = 'conference', 'Conference'
    WORKSHOP = 'workshop', 'Workshop'
    SEMINAR = 'seminar', 'Seminar'
    CONCERT = 'concert', 'Concert'
    PARTY = 'party', 'Party'
    NETWORKING = 'networking', 'Networking'
    SPORTS = 'sports', 'Sports'
    OTHER = 'other', 'Other'


class SeatArrangement(models.TextChoices):
    GENERAL = 'general', 'General Admission'
    RESERVED = 'reserved', 'Reserved Seating'
    # TABLE = 'table', 'Table Seating'
    # VIP = 'vip', 'VIP Sections'


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='events')
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True, default='')
    venue = models.CharField(max_length=300)
    date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    banner = models.ImageField(upload_to='event_banners/', blank=True, null=True)
    category = models.CharField(max_length=20, choices=EventCategory.choices, default=EventCategory.OTHER)
    max_capacity = models.PositiveIntegerField(default=100)
    seat_arrangement = models.CharField(max_length=20, choices=SeatArrangement.choices, default=SeatArrangement.GENERAL)
    vip_support = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    is_listed = models.BooleanField(default=False, help_text="Show this event in the public marketplace browse page and homepage.")
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='suspended_events')
    admin_flags = models.JSONField(default=list, blank=True)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    host_subaccount_code = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        ordering = ['-date']
        verbose_name = 'Event'
        verbose_name_plural = 'Events'

        indexes = [
            models.Index(fields=['host', '-date'], name='event_host_date_idx'),
            models.Index(fields=['date'], name='event_date_idx'),
            models.Index(fields=['category'], name='event_category_idx'),
            models.Index(fields=['is_suspended', 'is_archived'], name='event_admin_flags_idx'),
            models.Index(fields=['is_published', 'is_listed', 'date'], name='event_public_idx'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:50]
            self.slug = f"{base}-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    @property
    def registered_guests(self):
        return self.guests.count()

    @property
    def checked_in_guests(self):
        return self.guests.filter(checked_in=True).count()

    @property
    def attendance_rate(self):
        total = self.registered_guests
        if total == 0:
            return 0
        return round((self.checked_in_guests / total) * 100, 1)

    @property
    def available_seats(self):
        return max(0, self.max_capacity - self.registered_guests)

    @property
    def is_full(self):
        return self.registered_guests >= self.max_capacity

    @property
    def is_active_now(self):
        from django.utils import timezone
        return self.date > timezone.now() and not self.is_suspended and not self.is_archived


    @property
    def is_draft(self):
        """Not yet published — invisible to guests even by direct link."""
        return not self.is_published

    @property
    def is_discoverable(self):
        """
        Publicly discoverable in browse/landing.
        Requires: published AND listed AND not archived AND not suspended.
        """
        return (
            self.is_published
            and self.is_listed
            and not self.is_archived
            and not self.is_suspended
        )


    @property
    def is_completed(self):
        from django.utils import timezone
        return self.date < timezone.now()

    @property
    def total_budget(self):
        total = 0
        try:
            budget = Budget.objects.get(event=self)
            total = budget.total_budget
        except Budget.DoesNotExist:
            pass
        return total

    @property
    def total_spent(self):
        return Expense.objects.filter(event=self).aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def is_paid(self):
        return self.price is not None and self.price > 0
    
    @property
    def platform_commission(self):
        """5% commission on paid events"""
        if self.price:
            return (self.price * Decimal('0.05')).quantize(Decimal('0.01'))
        return Decimal('0.00')
    
    @property
    def host_earnings(self):
        """What the host receives after commission"""
        if self.price:
            return self.price - self.platform_commission
        return Decimal('0.00')


class Budget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='budget')
    total_budget = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='USD')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Event Budget'

    def __str__(self):
        return f"Budget for {self.event.name}"

    @property
    def spent(self):
        total = self.event.expenses.aggregate(models.Sum('amount'))['amount__sum'] or 0
        return total

    @property
    def remaining(self):
        return self.total_budget - self.spent

    @property
    def utilization_percent(self):
        if self.total_budget == 0:
            return 0
        return round((float(self.spent) / float(self.total_budget)) * 100, 1)


class Expense(models.Model):
    class Category(models.TextChoices):
        VENUE = 'venue', 'Venue'
        CATERING = 'catering', 'Catering'
        DECORATION = 'decoration', 'Decoration'
        PHOTOGRAPHY = 'photography', 'Photography'
        VIDEOGRAPHY = 'videography', 'Videography'
        ENTERTAINMENT = 'entertainment', 'Entertainment'
        STAFFING = 'staffing', 'Staffing'
        MARKETING = 'marketing', 'Marketing'
        EQUIPMENT = 'equipment', 'Equipment'
        TRANSPORT = 'transport', 'Transportation'
        MISC = 'misc', 'Miscellaneous'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='expenses')
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    title = models.CharField(max_length=300)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.MISC)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    description = models.TextField(blank=True, default='')
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)
    paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    vendor_name = models.CharField(max_length=300, blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event.name} - {self.title} ({self.amount})"


class Seat(models.Model):
    """
    A single seat at an event.

    Lifecycle:
      available  -> auto-assigner may pick it (no guest, no hold)
      held       -> host reserved it for a named person (no guest yet)
      taken      -> a guest is assigned
      blocked    -> permanently unusable (broken, removed, etc.)

    The auto-assigner (guest registration) only ever picks 'available'
    seats with no guest attached. Held and blocked seats are never
    handed to walk-in guests.
    """

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        HELD      = 'held',      'Held'
        TAKEN     = 'taken',     'Taken'
        BLOCKED   = 'blocked',   'Blocked'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='seats',
    )
    label = models.CharField(
        max_length=50,
        help_text="Human-readable seat identifier, e.g. 'A-1', 'Table 3 Chair B'",
    )
    section = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Optional grouping, e.g. 'Family', 'VIP', 'Front row'",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    guest = models.OneToOneField(
        'guest.Guest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_seat',
        help_text="Set when a guest is assigned to this seat.",
    )
    held_for = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="When status is 'held', who the seat is reserved for.",
    )
    held_note = models.TextField(
        blank=True,
        default='',
        help_text="Optional note about the hold.",
    )
    access_code = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Optional. Guests who enter this code during registration "
                  "get seated in this group automatically.",
        db_index=True,
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Controls display order; lower numbers come first.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'label']
        verbose_name = 'Seat'
        verbose_name_plural = 'Seats'
        indexes = [
            models.Index(fields=['event', 'status'], name='seat_event_status_idx'),
            models.Index(fields=['event', 'section'], name='seat_event_section_idx'),
            models.Index(fields=['event', 'sort_order'], name='seat_event_order_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'label'],
                name='unique_seat_label_per_event',
            ),
        ]

    def __str__(self):
        return f"{self.event.name} · {self.label}"

    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE and self.guest_id is None

    @property
    def is_held(self):
        return self.status == self.Status.HELD

    @property
    def is_taken(self):
        return self.status == self.Status.TAKEN or self.guest_id is not None



def next_available_seat(event):
    """
    Return the next seat that can be auto-assigned, or None.

    Rules:
      - Only 'available' seats with no guest attached.
      - Ordered by sort_order, then label (so 'A-1' before 'A-2').
      - Returns None if there are no available seats.
    """
    return (
        Seat.objects
        .filter(
            event=event,
            status=Seat.Status.AVAILABLE,
            guest__isnull=True,
        )
        .order_by('sort_order', 'label')
        .first()
    )

def find_held_seat_by_code(event, code):
    """
    Return the next held seat for the given access code, or None.

    Matching is case-insensitive and strips whitespace. Only seats with
    status='held' and no guest assigned are eligible.

    Order is 'sort_order' then 'label', so the host controls which seat
    gets handed out first by the order they created them.
    """
    if not code:
        return None

    code = code.strip()
    if not code:
        return None

    return (
        Seat.objects
        .filter(
            event=event,
            status=Seat.Status.HELD,
            guest__isnull=True,
            access_code__iexact=code,
        )
        .order_by('sort_order', 'label')
        .first()
    )