from decimal import Decimal
import uuid
import requests
import logging

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from .models import Guest
from event.models import Event, find_held_seat_by_code, next_available_seat
from core.emails import send_ticket_email


logger = logging.getLogger(__name__)


@transaction.atomic
def guest_register(request, event_id):
    """Free-event registration. Locks the event row to prevent overselling."""
    if request.method == 'POST':
        event = get_object_or_404(
            Event.objects.select_for_update(),
            id=event_id, is_published=True,
        )
    else:
        event = get_object_or_404(Event, id=event_id, is_published=True)

    if event.is_suspended:
        return render(request, 'guests/full.html', {'event': event, 'suspended': True})

    if event.is_full:
        return render(request, 'guests/full.html', {'event': event})

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        meal_preference = request.POST.get('meal_preference', '').strip()
        plus_one = request.POST.get('plus_one') == 'on'
        notes = request.POST.get('notes', '').strip()

        if not all([full_name, email]):
            messages.error(request, 'Name and email are required.')
            return render(request, 'guests/register.html', {'event': event})

        if Guest.objects.filter(event=event, email=email).exists():
            messages.error(request, 'This email is already registered for this event.')
            return render(request, 'guests/register.html', {'event': event})

        # ---- Seat assignment happens here, atomically ----
        access_code = request.POST.get('access_code', '').strip()

        seat = None
        if event.seat_arrangement != 'general':
            # 1. If the guest entered an access code, try to match a held seat
            if access_code:
                seat = find_held_seat_by_code(event, access_code)

            # 2. Otherwise fall back to the next available seat
            if seat is None:
                seat = next_available_seat(event)

            if seat is None:
                messages.error(
                    request,
                    'Sorry — all seats for this event are taken. '
                    'Please contact the organizer if you think this is a mistake.'
                )
                return render(request, 'guests/register.html', {'event': event})

        guest = Guest.objects.create(
            event=event,
            full_name=full_name,
            email=email,
            phone=phone,
            meal_preference=meal_preference,
            plus_one=plus_one,
            notes=notes,
            payment_status='paid',
            amount_paid=Decimal('0.00'),
            seat_number=seat.label if seat else '',
        )

        if seat:
            seat.guest = guest
            seat.status = 'taken'
            seat.access_code = ''  # Clear the access code after assignment
            seat.save(update_fields=['guest', 'status', 'access_code'])

        # ---- Send the ticket email (no account, just the link) ----
        # Runs for ALL events — general or reserved — because guests
        # need their ticket URL regardless of whether a seat was assigned.
        try:
            send_ticket_email(guest=guest)
        except Exception as exc:
            logger.warning('Ticket email failed for guest %s: %s', guest.id, exc)

        messages.success(request, 'Registration successful! Your ticket is ready.')
        return redirect('guest_ticket', guest_id=guest.id)

    return render(request, 'guests/register.html', {'event': event})


@transaction.atomic
def register_for_paid_event(request, event_id):
    """Paid-event registration. Locks the event row and assigns a seat."""
    if request.method == 'POST':
        event = get_object_or_404(
            Event.objects.select_for_update(),
            id=event_id, is_published=True,
        )
    else:
        event = get_object_or_404(Event, id=event_id, is_published=True)

    if event.is_suspended:
        return render(request, 'guests/full.html', {'event': event, 'suspended': True})

    if event.is_full:
        return render(request, 'guests/full.html', {'event': event})

    if not event.is_paid:
        return redirect('guest_register', event_id=event.id)

    if not event.host_subaccount_code:
        messages.error(
            request,
            'This host has not connected a payout account yet. '
            'Please contact the organizer.',
        )
        return render(request, 'guests/register.html', {'event': event})

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        meal_preference = request.POST.get('meal_preference', '').strip()
        plus_one = request.POST.get('plus_one') == 'on'
        notes = request.POST.get('notes', '').strip()

        if not all([full_name, email]):
            messages.error(request, 'Name and email are required.')
            return render(request, 'guests/register.html', {'event': event})

        if Guest.objects.filter(event=event, email=email).exists():
            messages.error(request, 'This email is already registered for this event.')
            return render(request, 'guests/register.html', {'event': event})

        # ---- Seat assignment happens here, atomically ----
        access_code = request.POST.get('access_code', '').strip()

        seat = None
        if event.seat_arrangement != 'general':
            # 1. If the guest entered an access code, try to match a held seat
            if access_code:
                seat = find_held_seat_by_code(event, access_code)

            # 2. Otherwise fall back to the next available seat
            if seat is None:
                seat = next_available_seat(event)

            if seat is None:
                messages.error(
                    request,
                    'Sorry — all seats for this event are taken. '
                    'Please contact the organizer if you think this is a mistake.'
                )
                return render(request, 'guests/register.html', {'event': event})

        guest = Guest.objects.create(
            event=event,
            full_name=full_name,
            email=email,
            phone=phone,
            meal_preference=meal_preference,
            plus_one=plus_one,
            notes=notes,
            payment_status='pending',
            seat_number=seat.label if seat else '',
        )

        # Reserve the seat immediately, so no one else grabs it while
        # this guest is paying. If payment fails, the seat stays taken
        # until we release it explicitly (see error paths below).
        if seat:
            seat.guest = guest
            seat.status = 'taken'
            seat.access_code = ''  # Clear the access code after assignment
            seat.save(update_fields=['guest', 'status', 'access_code'])

        reference = f'EF-{uuid.uuid4().hex[:12].upper()}'
        payload = {
            'email': guest.email,
            'amount': int(event.price * 100),
            'reference': reference,
            'callback_url': request.build_absolute_uri(
                reverse('payment_callback', args=[guest.id])
            ),
            'subaccount': event.host_subaccount_code,
            'bearer': 'subaccount',
            'metadata': {
                'guest_id': str(guest.id),
                'event_id': str(event.id),
                'event_name': event.name,
            },
        }

        try:
            response = requests.post(
                'https://api.paystack.co/transaction/initialize',
                json=payload,
                headers={
                    'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                    'Content-Type': 'application/json',
                },
                timeout=15,
            )
            data = response.json()
        except requests.RequestException:
            messages.error(request, 'Could not reach the payment provider. Please try again.')
            # Release the seat before deleting the guest.
            # FIX: was status='taken' — should be 'available' so the seat
            # goes back into the pool.
            if seat:
                seat.guest = None
                seat.status = 'available'
                seat.access_code = ''
                seat.save(update_fields=['guest', 'status', 'access_code'])
            guest.delete()
            return render(request, 'guests/register.html', {'event': event})

        if not data.get('status'):
            messages.error(request, data.get('message') or 'Payment could not be initialized.')
            if seat:
                seat.guest = None
                seat.status = 'available'
                seat.access_code = ''
                seat.save(update_fields=['guest', 'status', 'access_code'])
            guest.delete()
            return render(request, 'guests/register.html', {'event': event})

        guest.payment_reference = reference
        guest.save(update_fields=['payment_reference'])

        return redirect(data['data']['authorization_url'])

    return render(request, 'guests/register.html', {'event': event})


def payment_callback(request, guest_id):
    """Paystack redirects here after payment. Verify server-side, then update."""
    guest = get_object_or_404(Guest, id=guest_id)

    # Idempotency — if already paid, don't re-verify or re-email
    if guest.payment_status == 'paid':
        return redirect('guest_ticket', guest_id=guest.id)

    if not guest.payment_reference:
        messages.error(request, 'Payment reference missing.')
        return redirect('guest_register', event_id=guest.event_id)

    try:
        response = requests.get(
            f'https://api.paystack.co/transaction/verify/{guest.payment_reference}',
            headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'},
            timeout=15,
        )
        data = response.json()
    except requests.RequestException:
        messages.warning(request, 'Could not verify your payment. Please refresh in a moment.')
        return redirect('guest_ticket', guest_id=guest.id)

    payment_data = data.get('data', {})

    if data.get('status') and payment_data.get('status') == 'success':
        guest.payment_status = 'paid'
        guest.amount_paid = Decimal(payment_data['amount']) / 100
        guest.save(update_fields=['payment_status', 'amount_paid'])

        # ---- Send the ticket email now that payment is confirmed ----
        try:
            send_ticket_email(guest=guest)
        except Exception as exc:
            logger.warning('Ticket email failed for guest %s: %s', guest.id, exc)

        messages.success(request, 'Payment successful! Your ticket is ready.')
        return redirect('guest_ticket', guest_id=guest.id)

    guest.payment_status = 'failed'
    guest.save(update_fields=['payment_status'])
    return render(request, 'guests/payment_failed.html', {'guest': guest})


def event_register(request, event_id):
    """Routes to free or paid registration based on event price."""
    event = get_object_or_404(Event, id=event_id, is_published=True)
    if event.is_paid:
        return register_for_paid_event(request, event_id)
    return guest_register(request, event_id)


def guest_ticket(request, guest_id):
    guest = get_object_or_404(Guest, id=guest_id)
    return render(request, 'guests/ticket.html', {'guest': guest})