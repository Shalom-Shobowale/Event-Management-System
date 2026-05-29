from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views
from event import views as event_views
from guest import views as guest_views
from ticket import views as ticket_views
from vendors import views as vendor_views
from bookings import views as booking_views
from collaboration import views as collab_views
from event import views as budget_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Landing
    path('', core_views.landing, name='landing'),

    # Auth
    path('register/', core_views.register_view, name='register'),
    path('login/', core_views.login_view, name='login'),
    path('logout/', core_views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', core_views.dashboard, name='dashboard'),

    # Profile
    path('profile/', core_views.profile_view, name='profile'),
    path('profile/password/', core_views.change_password_view, name='change_password'),

    # Events
    path('events/create/', event_views.create_event, name='create_event'),
    path('events/', event_views.event_lists, name='event_lists'),
    path('events/<uuid:event_id>/', event_views.event_dashboard, name='event_dashboard'),
    path('events/<uuid:event_id>/edit/', event_views.edit_event, name='edit_event'),
    path('events/<uuid:event_id>/delete/', event_views.delete_event, name='delete_event'),
    path('events/<uuid:event_id>/export/', event_views.export_guests, name='export_guests'),

    # Event Vendors & Procurement
    path('events/<uuid:event_id>/vendors/', booking_views.event_bookings, name='event_vendors'),
    path('events/<uuid:event_id>/vendors/rfq/', booking_views.create_quote_request, name='create_quote_request'),

    # Guest Registration (public)
    path('events/<uuid:event_id>/register/', guest_views.guest_register, name='guest_register'),
    path('ticket/<uuid:guest_id>/', guest_views.guest_ticket, name='guest_ticket'),

    # Ticket Validation
    path('validate/<str:ticket_code>/', ticket_views.validate_ticket, name='validate_ticket'),
    path('scanner/', ticket_views.scanner, name='scanner'),
    path('api/validate/<str:ticket_code>/', ticket_views.api_validate, name='api_validate'),

    # Analytics
    path('analytics/', event_views.analytics, name='analytics'),

    # ========== VENDOR MARKETPLACE ==========

    # Vendor Registration & Dashboard
    path('vendors/register/', vendor_views.vendor_register, name='vendor_register'),
    path('vendors/dashboard/', vendor_views.vendor_dashboard, name='vendor_dashboard'),
    path('vendors/services/add/', vendor_views.add_service, name='add_service'),
    path('vendors/portfolio/add/', vendor_views.add_portfolio, name='add_portfolio'),


    # Marketplace
    path('vendors/', vendor_views.marketplace, name='vendor_marketplace'),
    path('vendors/<slug:slug>/', vendor_views.vendor_profile, name='vendor_profile'),
    path('vendors/<uuid:vendor_id>/save/', vendor_views.save_vendor, name='save_vendor'),
    path('vendors/<uuid:vendor_id>/review/', vendor_views.submit_review, name='submit_review'),

    # Saved Vendors
    path('vendors/saved/', vendor_views.saved_vendors, name='saved_vendors'),

    # ========== BOOKINGS & RFQ ==========

    # Quote Requests
    path('bookings/rfq/', booking_views.my_quote_requests, name='my_quote_requests'),
    path('bookings/rfq/<uuid:rfq_id>/', booking_views.quote_request_detail, name='quote_request_detail'),
    path('bookings/rfq/<uuid:rfq_id>/submit/', booking_views.submit_proposal, name='submit_proposal'),
    path('bookings/rfq/proposals/', booking_views.vendor_proposals, name='vendor_proposals'),

    # Bookings
    path('bookings/<uuid:booking_id>/', booking_views.booking_detail, name='booking_detail'),
    path('bookings/<uuid:booking_id>/confirm/', booking_views.confirm_booking, name='confirm_booking'),
    path('bookings/<uuid:booking_id>/complete/', booking_views.complete_booking, name='complete_booking'),
    path('bookings/<uuid:booking_id>/cancel/', booking_views.cancel_booking, name='cancel_booking'),
    path('bookings/vendor/', booking_views.vendor_bookings, name='vendor_bookings'),

    # Proposals
    path('proposals/<uuid:proposal_id>/accept/', booking_views.accept_proposal, name='accept_proposal'),

    # ========== COLLABORATION ==========

    # Tasks
    path('events/<uuid:event_id>/tasks/', collab_views.event_tasks, name='event_tasks'),
    path('events/<uuid:event_id>/tasks/create/', collab_views.create_task, name='create_task'),
    path('tasks/<uuid:task_id>/edit/', collab_views.update_task, name='update_task'),
    path('tasks/<uuid:task_id>/complete/', collab_views.complete_task, name='complete_task'),

    # Workspace
    path('events/<uuid:event_id>/workspace/', collab_views.event_workspace, name='event_workspace'),
    path('events/<uuid:event_id>/notes/add/', collab_views.add_note, name='add_note'),
    path('events/<uuid:event_id>/files/upload/', collab_views.upload_file, name='upload_file'),
    path('events/<uuid:event_id>/members/add/', collab_views.add_member, name='add_member'),

    # Messages
    path('messages/', collab_views.conversations, name='conversations'),
    path('messages/<uuid:conversation_id>/', collab_views.conversation_detail, name='conversation_detail'),
    path('events/<uuid:event_id>/messages/start/', collab_views.start_conversation, name='start_conversation'),

    # ========== BUDGET ==========

    # Budget
    path('events/<uuid:event_id>/budget/', event_views.event_budget, name='event_budget'),
    path('events/<uuid:event_id>/budget/update/', event_views.update_budget, name='update_budget'),
    path('events/<uuid:event_id>/budget/expense/', event_views.add_expense, name='add_expense'),
    path('expenses/<uuid:expense_id>/edit/', event_views.edit_expense, name='edit_expense'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
