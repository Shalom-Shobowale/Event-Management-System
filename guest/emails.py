# guest/emails.py
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_ticket_email(guest):
    """Send the guest their ticket confirmation."""
    subject = f'Your ticket for {guest.event.name}'
    html = render_to_string('guests/emails/ticket_email.html', {'guest': guest})
    text = f'Your ticket for {guest.event.name}. Ticket ID: {guest.ticket_code}'

    send_mail(
        subject=subject,
        message=text,
        html_message=html,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[guest.email],
        fail_silently=False,
    )