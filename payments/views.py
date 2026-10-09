from decimal import Decimal
import hmac
import hashlib
import json
import logging

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from guest.models import Guest
from .models import HostPaymentAccount


logger = logging.getLogger(__name__)


def _paystack_headers():
    return {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Handle Paystack webhooks. Always return 200 to prevent retries."""
    payload = request.body
    signature = request.headers.get('x-paystack-signature')

    if not signature:
        return HttpResponse(status=400)

    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        return HttpResponse(status=400)

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    if event.get('event') == 'charge.success':
        data = event.get('data', {})
        reference = data.get('reference')

        if not reference:
            return HttpResponse(status=200)

        try:
            guest = Guest.objects.get(payment_reference=reference)
        except Guest.DoesNotExist:
            return HttpResponse(status=200)

        if guest.payment_status == 'paid':
            return HttpResponse(status=200)

        guest.payment_status = 'paid'
        guest.amount_paid = Decimal(data.get('amount', 0)) / 100
        guest.save(update_fields=['payment_status', 'amount_paid'])

        # Send ticket email (defensively — don't fail webhook if email breaks)
        try:
            _send_ticket_email(guest)
        except Exception:
            logger.exception('Failed to send ticket email for guest %s', guest.id)

    return HttpResponse(status=200)


def _send_ticket_email(guest):
    """Send the ticket email via Anymail/Resend."""
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    ticket_url = f"{site_url}{reverse('guest_ticket', kwargs={'guest_id': guest.id})}"

    context = {
        'guest': guest,
        'event': guest.event,
        'ticket_url': ticket_url,
    }

    html_content = render_to_string('guests/emails/ticket_email.html', context)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject=f"Your ticket for {guest.event.name}",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[guest.email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)


@login_required
def connect_bank_account(request):
    if request.method == 'POST':
        bank_code = request.POST.get('bank_code', '').strip()
        account_number = request.POST.get('account_number', '').strip()
        bank_name = request.POST.get('bank_name', '').strip()

        if not all([bank_code, account_number]):
            messages.error(request, 'Select a bank and enter your account number.')
            return redirect('connect_bank_account')

        # Verify account with Paystack
        url = f'https://api.paystack.co/bank/resolve?account_number={account_number}&bank_code={bank_code}'
        try:
            resp = requests.get(url, headers=_paystack_headers(), timeout=15)
            data = resp.json()
        except requests.RequestException:
            messages.error(request, 'Could not reach Paystack. Try again.')
            return redirect('connect_bank_account')

        if not data.get('status'):
            messages.error(request, data.get('message') or 'Could not verify account.')
            return redirect('connect_bank_account')

        account_name = data['data']['account_name']

        # Create Paystack subaccount
        url = 'https://api.paystack.co/subaccount'
        payload = {
            'business_name': account_name,
            'settlement_bank': bank_code,
            'account_number': account_number,
            'percentage_charge': 5.0,
            'description': f'EventzUp host: {request.user.username}',
        }
        try:
            resp = requests.post(url, json=payload, headers=_paystack_headers(), timeout=15)
            data = resp.json()
        except requests.RequestException:
            messages.error(request, 'Could not reach Paystack. Try again.')
            return redirect('connect_bank_account')

        if not data.get('status'):
            messages.error(request, data.get('message') or 'Could not create payout account.')
            return redirect('connect_bank_account')

        subaccount_code = data['data']['subaccount_code']

        HostPaymentAccount.objects.update_or_create(
            host=request.user,
            defaults={
                'subaccount_code': subaccount_code,
                'bank_code': bank_code,
                'bank_name': bank_name,
                'account_number': account_number,
                'account_name': account_name,
                'is_verified': True,
            },
        )

        messages.success(request, f'Bank account connected: {account_name}')
        return redirect('dashboard')

    # GET — fetch bank list
    url = 'https://api.paystack.co/bank?country=nigeria'
    banks = []
    try:
        resp = requests.get(url, headers=_paystack_headers(), timeout=15)
        data = resp.json()
        if data.get('status'):
            banks = data['data']
    except requests.RequestException:
        pass

    return render(request, 'payments/connect_bank.html', {'banks': banks})