from django.contrib import admin
from .models import Host
from .verification_models import EmailVerification, PhoneVerification, VendorDocument, UserNotification


@admin.register(Host)
class HostAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'verification_level', 'is_suspended', 'is_staff')
    list_filter = ('is_suspended', 'verification_level', 'is_staff')
    search_fields = ('username', 'email')


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_verified', 'expires_at', 'created_at')
    list_filter = ('is_verified',)
    search_fields = ('user__username', 'user__email')


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'is_verified', 'expires_at', 'created_at')
    list_filter = ('is_verified',)
    search_fields = ('user__username', 'phone')


@admin.register(VendorDocument)
class VendorDocumentAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'doc_type', 'status', 'created_at')
    list_filter = ('status', 'doc_type')
    search_fields = ('vendor__business_name', 'name')


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__username', 'title')
