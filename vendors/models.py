import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify


class VendorCategory(models.TextChoices):
    CATERING = 'catering', 'Food & Catering'
    PHOTOGRAPHY = 'photography', 'Photography'
    VIDEOGRAPHY = 'videography', 'Videography'
    DECORATION = 'decoration', 'Decoration'
    EVENT_PLANNING = 'planning', 'Event Planning'
    DJ_SERVICES = 'dj', 'DJ Services'
    LIVE_BAND = 'band', 'Live Bands'
    MC_SERVICES = 'mc', 'MC Services'
    VENUE = 'venue', 'Venue Providers'
    EQUIPMENT = 'equipment', 'Equipment Rentals'
    SECURITY = 'security', 'Security Services'
    TRANSPORT = 'transport', 'Transportation'
    BEAUTY = 'beauty', 'Makeup & Beauty'
    SOUND_LIGHT = 'sound_light', 'Lighting & Sound'
    STAFFING = 'staffing', 'Event Staffing'
    OTHER = 'other', 'Custom Services'


class Vendor(models.Model):
    class VerificationStatus(models.TextChoices):
        UNVERIFIED = 'unverified', 'Unverified'
        PENDING = 'pending', 'Pending Review'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vendor_profile')
    business_name = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to='vendor_logos/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='vendor_covers/', blank=True, null=True)
    description = models.TextField(blank=True, default='')
    categories = models.CharField(max_length=500, blank=True, default='')  # Comma-separated categories

    # Contact Information
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    website = models.URLField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=100, blank=True, default='')
    country = models.CharField(max_length=100, blank=True, default='')
    service_radius_km = models.PositiveIntegerField(default=50)

    # Business Details
    years_in_business = models.PositiveIntegerField(default=0)
    team_size = models.PositiveIntegerField(default=1)
    business_license = models.CharField(max_length=200, blank=True, default='')

    # Verification
    verification_status = models.CharField(max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.UNVERIFIED)
    verified_at = models.DateTimeField(null=True, blank=True)

    # Metrics
    total_bookings = models.PositiveIntegerField(default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    response_time_hours = models.PositiveIntegerField(default=24)

    # Settings
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    auto_accept_bookings = models.BooleanField(default=False)
    min_notice_days = models.PositiveIntegerField(default=3)

    # Social Links
    instagram = models.URLField(blank=True, default='')
    facebook = models.URLField(blank=True, default='')
    twitter = models.URLField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-average_rating', '-total_bookings']

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.business_name)[:50]
            self.slug = f"{base}-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    @property
    def rating_stars(self):
        return round(float(self.average_rating))

    @property
    def category_list(self):
        return [c.strip() for c in self.categories.split(',') if c.strip()]


class Service(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=300)
    category = models.CharField(max_length=20, choices=VendorCategory.choices)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    price_unit = models.CharField(max_length=20, default='per event')
    duration_hours = models.PositiveIntegerField(default=4)
    min_guests = models.PositiveIntegerField(default=0)
    max_guests = models.PositiveIntegerField(default=1000)
    includes = models.TextField(blank=True, default='')  # What's included
    requirements = models.TextField(blank=True, default='')  # What client needs to provide
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f"{self.vendor.business_name} - {self.name}"


class PortfolioItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='portfolio')
    title = models.CharField(max_length=300, blank=True, default='')
    description = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='portfolio/')
    event_name = models.CharField(max_length=300, blank=True, default='')
    event_date = models.DateField(null=True, blank=True)
    tags = models.CharField(max_length=500, blank=True, default='')
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return f"{self.vendor.business_name} - {self.title or 'Portfolio Item'}"


class VendorAvailability(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='availability')
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ['vendor', 'date']
        ordering = ['date']

    def __str__(self):
        status = "Available" if self.is_available else "Unavailable"
        return f"{self.vendor.business_name} - {self.date} - {status}"


class VendorReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='reviews')
    event = models.ForeignKey('event.Event', on_delete=models.SET_NULL, null=True, blank=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(default=5)  # 1-5
    professionalism = models.PositiveIntegerField(default=5)
    quality = models.PositiveIntegerField(default=5)
    communication = models.PositiveIntegerField(default=5)
    timeliness = models.PositiveIntegerField(default=5)
    title = models.CharField(max_length=300, blank=True, default='')
    comment = models.TextField(blank=True, default='')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['vendor', 'event', 'reviewer']

    def __str__(self):
        return f"{self.vendor.business_name} - {self.rating} stars by {self.reviewer}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update vendor average rating
        reviews = VendorReview.objects.filter(vendor=self.vendor)
        avg = reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0
        self.vendor.average_rating = round(avg, 2)
        self.vendor.total_reviews = reviews.count()
        self.vendor.save(update_fields=['average_rating', 'total_reviews'])


class SavedVendor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_vendors')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='saved_by')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'vendor']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} saved {self.vendor.business_name}"
