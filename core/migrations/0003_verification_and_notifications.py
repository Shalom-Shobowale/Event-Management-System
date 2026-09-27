from django.db import migrations, models
from django.conf import settings
import uuid
import core.verification_models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_host_is_suspended_host_phone_verified_and_more'),
        ('vendors', '0002_vendor_admin_notes_vendor_badge_vendor_is_suspended_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailVerification',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False, default=uuid.uuid4, editable=False)),
                ('code', models.CharField(max_length=6, default=core.verification_models._generate_code)),
                ('token', models.CharField(max_length=32, default=core.verification_models._generate_token, unique=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='email_verifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='PhoneVerification',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False, default=uuid.uuid4, editable=False)),
                ('phone', models.CharField(max_length=20)),
                ('code', models.CharField(max_length=6, default=core.verification_models._generate_code)),
                ('is_verified', models.BooleanField(default=False)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='phone_verifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='VendorDocument',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False, default=uuid.uuid4, editable=False)),
                ('doc_type', models.CharField(max_length=20, choices=[('license', 'Business License'), ('id', 'ID Proof'), ('insurance', 'Insurance Certificate'), ('cert', 'Professional Certification'), ('other', 'Other Document')], default='other')),
                ('file', models.FileField(upload_to='vendor_docs/')),
                ('name', models.CharField(max_length=300)),
                ('status', models.CharField(max_length=20, choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('vendor', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='documents', to='vendors.vendor')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='UserNotification',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False, default=uuid.uuid4, editable=False)),
                ('notification_type', models.CharField(max_length=20, choices=[('event_reminder', 'Event Reminder'), ('booking_update', 'Booking Update'), ('verification', 'Verification Update'), ('support', 'Support Update'), ('announcement', 'Platform Announcement'), ('system', 'System Message')], default='system')),
                ('title', models.CharField(max_length=300)),
                ('message', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('link', models.CharField(blank=True, default='', max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
