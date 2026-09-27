from django.contrib import admin
from .models import (
    AdminRole, AuditLog, Report, SupportTicket, TicketReply,
    PlatformNotification, PlatformSettings, ServiceCategory,
    FeaturedVendor, SecurityEvent,
)

admin.site.register(AdminRole)
admin.site.register(AuditLog)
admin.site.register(Report)
admin.site.register(SupportTicket)
admin.site.register(TicketReply)
admin.site.register(PlatformNotification)
admin.site.register(PlatformSettings)
admin.site.register(ServiceCategory)
admin.site.register(FeaturedVendor)
admin.site.register(SecurityEvent)
