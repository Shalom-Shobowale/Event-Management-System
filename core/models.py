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

    def __str__(self):
        return self.get_full_name() or self.username
