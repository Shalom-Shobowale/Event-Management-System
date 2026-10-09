# payments/services.py
import requests
from django.conf import settings

def create_host_subaccount(host, bank_code, account_number):
    """Create a Paystack subaccount for a host to receive event payments"""
    url = 'https://api.paystack.co/subaccount'
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'business_name': host.get_full_name() or host.username,
        'settlement_bank': bank_code,
        'account_number': account_number,
        'percentage_charge': 5.0,  # Platform gets 5% on all payments to this host
        'description': f'EventzUp host: {host.username}'
    }
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    if data.get('status'):
        return data['data']['subaccount_code']
    raise Exception(data.get('message', 'Failed to create subaccount'))