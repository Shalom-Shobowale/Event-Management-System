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

    class Meta:
        ordering = ['seat_number']

    def __str__(self):
        return f"{self.full_name} - {self.event.name}"

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            self.ticket_code = f"EF-{self.event.slug[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
        if not self.seat_number:
            self.seat_number = self._assign_seat()
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.qr_code:
            self._generate_qr_code()

    def _assign_seat(self):
        existing = Guest.objects.filter(event=self.event).count()
        prefix = 'VIP' if self.event.vip_support and existing < 10 else 'G'
        return f"{prefix}-{existing + 1:03d}"

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
