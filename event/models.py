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
    TABLE = 'table', 'Table Seating'
    VIP = 'vip', 'VIP Sections'


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
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

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
