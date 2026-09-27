from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from core.verification_models import UserNotification


def notify_user(user, title, message, notification_type=UserNotification.Type.SYSTEM, link='', send_email=None):
    notif = UserNotification.notify(user, title, message, notification_type, link)
    should_email = send_email if send_email is not None else user.email_notifications
    if should_email and user.email:
        try:
            send_mail(
                subject=f'{settings.PLATFORM_NAME if hasattr(settings, "PLATFORM_NAME") else "EventFlow"}: {title}',
                message=strip_tags(message),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass
    return notif


def notify_booking_update(user, booking, title, message):
    return notify_user(
        user, title, message,
        notification_type=UserNotification.Type.BOOKING_UPDATE,
        link=f'/bookings/{booking.id}/',
    )


def notify_event_reminder(user, event, message):
    return notify_user(
        user, f'Reminder: {event.name}', message,
        notification_type=UserNotification.Type.EVENT_REMINDER,
        link=f'/events/{event.id}/',
    )


def notify_verification(user, title, message):
    return notify_user(
        user, title, message,
        notification_type=UserNotification.Type.VERIFICATION,
    )


def notify_support(user, ticket, message):
    return notify_user(
        user, f'Support Update: {ticket.subject}', message,
        notification_type=UserNotification.Type.SUPPORT,
    )
