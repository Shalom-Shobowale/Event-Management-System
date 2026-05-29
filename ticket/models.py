from django.db import models
from django.conf import settings
from guest.models import Guest


class CheckInLog(models.Model):
    class Status(models.TextChoices):
        VALID = 'valid', 'Valid'
        INVALID = 'invalid', 'Invalid'
        DUPLICATE = 'duplicate', 'Duplicate'

    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, related_name='check_in_logs')
    scanned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.VALID)
    scanned_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-scanned_at']

    def __str__(self):
        return f"{self.guest.full_name} - {self.status} - {self.scanned_at}"
