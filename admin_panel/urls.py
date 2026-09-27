from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),

    # User Management
    path('users/', views.admin_users, name='admin_users'),
    path('users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('users/<int:user_id>/action/', views.admin_user_action, name='admin_user_action'),

    # Host Verification
    path('host-verification/', views.admin_host_verification, name='admin_host_verification'),

    # Vendor Verification
    path('vendor-verification/', views.admin_vendor_verification, name='admin_vendor_verification'),
    path('vendors/<uuid:vendor_id>/', views.admin_vendor_detail, name='admin_vendor_detail'),
    path('vendors/<uuid:vendor_id>/action/', views.admin_vendor_action, name='admin_vendor_action'),

    # Event Monitoring
    path('events/', views.admin_events, name='admin_events'),
    path('events/<uuid:event_id>/action/', views.admin_event_action, name='admin_event_action'),

    # Reports & Trust
    path('reports/', views.admin_reports, name='admin_reports'),
    path('reports/<uuid:report_id>/action/', views.admin_report_action, name='admin_report_action'),

    # Audit Log
    path('audit/', views.admin_audit_log, name='admin_audit_log'),

    # Security
    path('security/', views.admin_security, name='admin_security'),
    path('security/<uuid:event_id>/action/', views.admin_security_action, name='admin_security_action'),

    # Support & Disputes
    path('support/', views.admin_support, name='admin_support'),
    path('support/<uuid:ticket_id>/', views.admin_support_detail, name='admin_support_detail'),
    path('support/<uuid:ticket_id>/action/', views.admin_support_action, name='admin_support_action'),

    # Notifications
    path('notifications/', views.admin_notifications, name='admin_notifications'),

    # Marketplace
    path('marketplace/', views.admin_marketplace, name='admin_marketplace'),
    path('marketplace/category/', views.admin_marketplace_category, name='admin_marketplace_category'),
    path('marketplace/feature/', views.admin_marketplace_feature, name='admin_marketplace_feature'),

    # Analytics
    path('analytics/', views.admin_analytics, name='admin_analytics'),

    # Settings
    path('settings/', views.admin_settings, name='admin_settings'),

    # Staff
    path('staff/', views.admin_staff, name='admin_staff'),
    path('staff/<int:user_id>/remove/', views.admin_staff_remove, name='admin_staff_remove'),

    # Payments
    path('payments/', views.admin_payments_dashboard, name='admin_payments_dashboard'),
    path('transactions/', views.admin_transactions, name='admin_transactions'),
    path('payouts/', views.admin_host_payouts, name='admin_host_payouts'),
    path('subscriptions/', views.admin_subscriptions, name='admin_subscriptions'),
]
