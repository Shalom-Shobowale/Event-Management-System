"""
Central email helpers.

Every transactional email goes through this module so subject lines,
from-addresses, and template paths stay consistent.

Emails defined here:
  - send_verification_email      (host/vendor — account email verification)
  - send_password_reset_email    (host/vendor — password reset)
  - send_welcome_email           (host/vendor — after signup, optional)
  - send_ticket_email            (guest — after registration, NO ACCOUNT)

Guests never get an account. The ticket email just delivers a URL to
the ticket page, which is already public (anyone with the link can see
it). No login, no verification, no account flow.
"""
import logging
from typing import Iterable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)


# ============================================================
# Base send helper
# ============================================================

def _send(
    *,
    subject: str,
    template_base: str,
    context: dict,
    to: Iterable[str],
    reply_to: list | None = None,
):
    """
    Render HTML + plain-text and send a single email.

    template_base should be a path WITHOUT extension, e.g.
    'emails/verification'. The helper will look for:
        templates/emails/verification.html
        templates/emails/verification.txt

    Failures are logged, never raised — a broken SMTP server must not
    crash a user's registration or login flow.
    """
    to = [e.strip() for e in to if e and e.strip()]
    if not to:
        logger.warning('Skipping email "%s" — no recipients', subject)
        return

    try:
        html_body = render_to_string(f'{template_base}.html', context)
        text_body = render_to_string(f'{template_base}.txt', context)
    except Exception as exc:
        logger.exception('Failed to render email "%s": %s', subject, exc)
        return

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to,
        reply_to=reply_to or None,
    )
    msg.attach_alternative(html_body, 'text/html')

    try:
        msg.send(fail_silently=False)
        logger.info('Sent email "%s" to %s', subject, to)
    except Exception as exc:
        logger.exception('Failed to send email "%s" to %s: %s', subject, to, exc)


# ============================================================
# Host / vendor emails (they have accounts)
# ============================================================

def send_verification_email(*, user, code: str):
    """Send the 6-digit email-verification code."""
    _send(
        subject='Verify your EventFlow email',
        template_base='emails/verification',
        context={
            'user': user,
            'code': code,
            'expires_in_hours': 24,
        },
        to=[user.email],
    )


def send_password_reset_email(*, user, reset_url: str):
    """Send a password reset link. `reset_url` is an absolute URL."""
    _send(
        subject='Reset your EventFlow password',
        template_base='emails/password_reset',
        context={
            'user': user,
            'reset_url': reset_url,
            'expires_in_hours': 24,
        },
        to=[user.email],
    )


def send_welcome_email(*, user):
    """Optional: sent after a host/vendor signs up."""
    _send(
        subject='Welcome to EventFlow',
        template_base='emails/welcome',
        context={'user': user},
        to=[user.email],
    )


# ============================================================
# Guest emails (NO ACCOUNT — ticket only)
# ============================================================

def send_ticket_email(*, guest):
    """
    Send a guest their ticket link.

    The guest does not have an account. This email just delivers the
    public ticket URL so they can retrieve their QR code later if
    they lose the page.
    """
    from django.urls import reverse

    ticket_path = reverse('guest_ticket', args=[guest.id])
    site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
    ticket_url = f'{site_url}{ticket_path}' if site_url else ticket_path

    _send(
        subject=f'Your ticket · {guest.event.name}',
        template_base='emails/ticket',
        context={
            'guest': guest,
            'event': guest.event,
            'ticket_url': ticket_url,
        },
        to=[guest.email],
    )