import uuid
import qrcode
from io import BytesIO
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from event.models import Event


class Guest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='guests')
    full_name = models.CharField(max_length=300)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, default='')
    meal_preference = models.CharField(max_length=100, blank=True, default='')
    plus_one = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default='')
    seat_number = models.CharField(max_length=50, blank=True, default='')
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    ticket_code = models.CharField(max_length=100, unique=True, blank=True)
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        default='pending'
    )
    payment_reference = models.CharField(max_length=100, blank=True, default='')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['seat_number']

    def __str__(self):
        return f"{self.full_name} - {self.event.name}"

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            self.ticket_code = f"EF-{self.event.slug[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
        # Seat assignment is handled in the registration views, not here,
        # because it requires a locked transaction over Seat + Guest together.
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.qr_code:
            self._generate_qr_code()



    def _assign_seat(self):
        """
        Auto-assign a seat from the event's seat pool.

        For 'general' seat_arrangement: no seat number is assigned.
        For 'reserved' (or table/vip later): pull the next available seat.

        Returns the seat label, or '' if no seat should be assigned.
        Raises ValueError if the arrangement is 'reserved' but no seat can
        be found — the caller should treat that as a booking failure.
        """
        from event.models import Seat, next_available_seat

        # General admission: no seat numbers
        if self.event.seat_arrangement == 'general':
            return ''

        # Reserved (and later: table, vip): pull from the seat pool
        seat = next_available_seat(self.event)
        if seat is None:
            # Caller must handle this — reservation is fully booked or unconfigured
            raise ValueError(
                'No available seats for this event. '
                'Registration cannot continue.'
            )

        # Mark the seat as taken by this guest, atomically (once save() completes).
        # We don't save the seat here — the guest doesn't have an ID yet.
        # We'll assign the seat's guest FK in guest_views after guest.save().
        self._pending_seat = seat
        return seat.label


    

    def _generate_qr_code(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(self.ticket_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f"qr_{self.ticket_code}.png"
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=True)

    def check_in(self):
        if self.checked_in:
            return False
        from django.utils import timezone
        self.checked_in = True
        self.checked_in_at = timezone.now()
        self.save()
        return True
