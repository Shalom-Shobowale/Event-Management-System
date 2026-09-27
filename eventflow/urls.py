from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core import views as core_views
from event import views as event_views
from guest import views as guest_views
from ticket import views as ticket_views
from vendors import views as vendor_views
from bookings import views as booking_views
from collaboration import views as collab_views
from admin_panel import views as admin_views
from core import verification_views as verify_views
from payments import views as payments_views


urlpatterns = [
    path('admin/', admin.site.urls),

    # Platform Admin Panel
    path('platform-admin/', include('admin_panel.urls')),

    # Landing
    path('', core_views.landing, name='landing'),

    # Reports
    path('reports/', include('reports.urls')),

    # Auth
    path('register/', core_views.register_view, name='register'),
    path('login/', core_views.login_view, name='login'),
    path('logout/', core_views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', core_views.dashboard, name='dashboard'),

    # Profile
    path('profile/', core_views.profile_view, name='profile'),
    path('profile/password/', core_views.change_password_view, name='change_password'),

    # Verification
    path('verify/email/send/', verify_views.send_email_verification, name='send_email_verification'),
    path('verify/email/', verify_views.verify_email, name='verify_email'),
    path('verify/phone/send/', verify_views.send_phone_verification, name='send_phone_verification'),
    path('verify/phone/', verify_views.verify_phone, name='verify_phone'),
    path('vendors/documents/upload/', verify_views.upload_vendor_document, name='upload_vendor_document'),

    # Notifications
    path('notifications/', verify_views.notification_center, name='notification_center'),
    path('notifications/<uuid:notification_id>/read/', verify_views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', verify_views.mark_all_notifications_read, name='mark_all_notifications_read'),

    # ========== EVENTS ==========
    path('events/create/', event_views.create_event, name='create_event'),
    path('events/<uuid:event_id>/', event_views.event_dashboard, name='event_dashboard'),
    path('events/<uuid:event_id>/edit/', event_views.edit_event, name='edit_event'),
    path('events/<uuid:event_id>/delete/', event_views.delete_event, name='delete_event'),
    path('events/<uuid:event_id>/export/', event_views.export_guests, name='export_guests'),
    path('e/<uuid:event_id>/', event_views.event_public, name='event_public'),
    path('events/', event_views.event_browse, name='event_browse'),
    path('my-events/', event_views.event_list, name='event_list'),
    path('events/<uuid:event_id>/archive/', event_views.event_archive, name='event_archive'),
    path('events/<uuid:event_id>/unarchive/', event_views.event_unarchive, name='event_unarchive'),
    path('events/<uuid:event_id>/seats/', event_views.event_seats, name='event_seats'),
    path('events/<uuid:event_id>/seats/generate/', event_views.event_seats_generate, name='event_seats_generate'),
    path('events/<uuid:event_id>/seats/hold/', event_views.event_seat_hold, name='event_seat_hold'),
    path('events/<uuid:event_id>/seats/release/', event_views.event_seat_release, name='event_seat_release'),
    path('events/<uuid:event_id>/seats/<uuid:seat_id>/assign/', event_views.event_seat_assign, name='event_seat_assign'),
    path('events/<uuid:event_id>/seats/<uuid:seat_id>/unassign/', event_views.event_seat_unassign, name='event_seat_unassign'),
    path('events/<uuid:event_id>/seats/search-guests/', event_views.event_seats_search_guests, name='event_seats_search_guests'),

    # Event Vendors & Procurement
    path('events/<uuid:event_id>/vendors/', booking_views.event_bookings, name='event_vendors'),
    path('events/<uuid:event_id>/vendors/rfq/', booking_views.create_quote_request, name='create_quote_request'),

    # ========== GUEST REGISTRATION (public) ==========
    path('events/<uuid:event_id>/register/', guest_views.event_register, name='event_register'),
    path('events/<uuid:event_id>/register/free/', guest_views.guest_register, name='guest_register'),
    path('events/<uuid:event_id>/register/paid/', guest_views.register_for_paid_event, name='register_for_paid_event'),
    path('ticket/<uuid:guest_id>/', guest_views.guest_ticket, name='guest_ticket'),
    path('payment/callback/<uuid:guest_id>/', guest_views.payment_callback, name='payment_callback'),

    # ========== TICKET VALIDATION ==========
    path('validate/<str:ticket_code>/', ticket_views.validate_ticket, name='validate_ticket'),
    path('scanner/', ticket_views.scanner, name='scanner'),
    path('api/validate/<str:ticket_code>/', ticket_views.api_validate, name='api_validate'),

    # Analytics
    path('analytics/', event_views.analytics, name='analytics'),

    # ========== VENDOR MARKETPLACE ==========
    path('vendors/', vendor_views.marketplace, name='vendor_marketplace'),
    path('vendors/saved/', vendor_views.saved_vendors, name='saved_vendors'),
    path('vendors/register/', vendor_views.vendor_register, name='vendor_register'),
    path('vendors/dashboard/', vendor_views.vendor_dashboard, name='vendor_dashboard'),
    path('vendors/profile/edit/', vendor_views.edit_vendor_profile, name='edit_vendor_profile'),
    path('vendors/services/add/', vendor_views.add_service, name='add_service'),
    path('vendors/portfolio/add/', vendor_views.add_portfolio, name='add_portfolio'),

    # Vendor subscription plans
    path('vendors/upgrade/', vendor_views.upgrade_plan, name='upgrade_plan'),
    path('vendors/subscribe/<int:plan_id>/', vendor_views.subscribe_to_plan, name='subscribe_to_plan'),
    path('vendors/subscription/callback/', vendor_views.subscription_callback, name='subscription_callback'),

    # Vendor actions (must come before the catch-all slug route)
    path('vendors/<uuid:vendor_id>/save/', vendor_views.save_vendor, name='save_vendor'),
    path('vendors/<uuid:vendor_id>/review/', vendor_views.submit_review, name='submit_review'),
    path('vendors/<uuid:vendor_id>/request-quote/', vendor_views.request_quote_vendor, name='request_quote_vendor'),
    path('vendors/<slug:slug>/', vendor_views.vendor_profile, name='vendor_profile'),

    # ========== BOOKINGS & RFQ ==========
    path('bookings/rfq/', booking_views.my_quote_requests, name='my_quote_requests'),
    path('bookings/rfq/browse/', booking_views.browse_rfqs, name='browse_rfqs'),
    path('bookings/rfq/<uuid:rfq_id>/', booking_views.quote_request_detail, name='quote_request_detail'),
    path('bookings/rfq/<uuid:rfq_id>/submit/', booking_views.submit_proposal, name='submit_proposal'),
    path('bookings/rfq/proposals/', booking_views.vendor_proposals, name='vendor_proposals'),

    path('bookings/<uuid:booking_id>/', booking_views.booking_detail, name='booking_detail'),
    path('bookings/<uuid:booking_id>/confirm/', booking_views.confirm_booking, name='confirm_booking'),
    path('bookings/<uuid:booking_id>/complete/', booking_views.complete_booking, name='complete_booking'),
    path('bookings/<uuid:booking_id>/cancel/', booking_views.cancel_booking, name='cancel_booking'),
    path('bookings/vendor/', booking_views.vendor_bookings, name='vendor_bookings'),

    path('proposals/<uuid:proposal_id>/accept/', booking_views.accept_proposal, name='accept_proposal'),

    # ========== COLLABORATION ==========
    path('events/<uuid:event_id>/tasks/', collab_views.event_tasks, name='event_tasks'),
    path('events/<uuid:event_id>/tasks/create/', collab_views.create_task, name='create_task'),
    path('tasks/<uuid:task_id>/edit/', collab_views.update_task, name='update_task'),
    path('tasks/<uuid:task_id>/complete/', collab_views.complete_task, name='complete_task'),

    path('events/<uuid:event_id>/workspace/', collab_views.event_workspace, name='event_workspace'),
    path('events/<uuid:event_id>/notes/add/', collab_views.add_note, name='add_note'),
    path('events/<uuid:event_id>/files/upload/', collab_views.upload_file, name='upload_file'),
    path('events/<uuid:event_id>/members/add/', collab_views.add_member, name='add_member'),

    path('messages/', collab_views.conversations, name='conversations'),
    path('messages/<uuid:conversation_id>/', collab_views.conversation_detail, name='conversation_detail'),
    path('events/<uuid:event_id>/messages/start/', collab_views.start_conversation, name='start_conversation'),

    # ========== BUDGET ==========
    path('events/<uuid:event_id>/budget/', event_views.event_budget, name='event_budget'),
    path('events/<uuid:event_id>/budget/update/', event_views.update_budget, name='update_budget'),
    path('events/<uuid:event_id>/budget/expense/', event_views.add_expense, name='add_expense'),
    path('expenses/<uuid:expense_id>/edit/', event_views.edit_expense, name='edit_expense'),

    # ========== PAYMENTS ==========
    path('payments/webhook/', payments_views.paystack_webhook, name='paystack_webhook'),
    path('payments/connect-bank/', payments_views.connect_bank_account, name='connect_bank_account'),

    # ========== Password ===========
    path('password-reset/', auth_views.PasswordResetView.as_view(
         template_name='auth/password_reset.html',
         email_template_name='emails/password_reset.txt',
         html_email_template_name='emails/password_reset.html',
         subject_template_name='emails/password_reset_subject.txt',
         success_url='/password-reset/done/',
     ),
     name='password_reset'),

    path('password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='auth/password_reset_done.html',
        ),
        name='password_reset_done'),

    path('reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='auth/password_reset_confirm.html',
            success_url='/reset/done/',
        ),
        name='password_reset_confirm'),

    path('reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='auth/password_reset_complete.html',
        ),
        name='password_reset_complete'),
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)