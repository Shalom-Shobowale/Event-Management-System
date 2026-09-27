import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from django.db import models


class Transaction(models.Model):
    class Type(models.TextChoices):
        BOOKING_PAYMENT = 'booking', 'Booking Payment'
        COMMISSION = 'commission', 'Platform Commission'
        VENDOR_PAYOUT = 'payout', 'Vendor Payout'
        REFUND = 'refund', 'Refund'
        WALLET_TOPUP = 'topup', 'Wallet Top-up'
        WALLET_WITHDRAWAL = 'withdrawal', 'Wallet Withdrawal'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        INITIATED = 'initiated', 'Initiated'
        SUCCESS = 'success', 'Successful'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'

    class Gateway(models.TextChoices):
        PAYSTACK = 'paystack', 'Paystack'
        FLUTTERWAVE = 'flutterwave', 'Flutterwave'
        STRIPE = 'stripe', 'Stripe'
        MANUAL = 'manual', 'Manual'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=100, unique=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    gateway = models.CharField(max_length=20, choices=Gateway.choices, default=Gateway.PAYSTACK)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='transactions')
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')

    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    commission_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    vendor_payout_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    gateway_reference = models.CharField(max_length=200, blank=True, default='')
    gateway_response = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    initiated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['booking']),
        ]

    def __str__(self):
        return f'{self.reference} - {self.amount} {self.currency} - {self.status}'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f'TXN-{uuid.uuid4().hex[:12].upper()}'
        super().save(*args, **kwargs)

    def mark_success(self, gateway_reference='', gateway_response=None):
        self.status = self.Status.SUCCESS
        self.gateway_reference = gateway_reference
        if gateway_response:
            self.gateway_response = gateway_response
        self.completed_at = timezone.now()
        self.save()

    def mark_failed(self, reason=''):
        self.status = self.Status.FAILED
        self.metadata['failure_reason'] = reason
        self.save()

    @property
    def is_successful(self):
        return self.status == self.Status.SUCCESS


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent'
        PAID = 'paid', 'Paid'
        PARTIAL = 'partial', 'Partially Paid'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    booking = models.ForeignKey('bookings.Booking', on_delete=models.CASCADE, related_name='invoices')
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='invoices')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='invoices')

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5.00'))
    commission_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    issued_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.invoice_number} - {self.total} {self.currency}'

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f'INV-{uuid.uuid4().hex[:8].upper()}'
        self.commission_amount = (self.subtotal * self.commission_rate) / Decimal('100')
        self.total = self.subtotal
        self.balance_due = self.total - self.amount_paid
        if self.balance_due <= 0 and self.amount_paid > 0:
            self.status = self.Status.PAID
            self.paid_at = timezone.now()
        elif self.amount_paid > 0:
            self.status = self.Status.PARTIAL
        super().save(*args, **kwargs)


class Refund(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        PROCESSED = 'processed', 'Processed'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='refunds')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds')
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    reason = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='processed_refunds')
    processed_at = models.DateTimeField(null=True, blank=True)
    gateway_reference = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Refund {self.amount} for {self.transaction.reference}'


class VendorPayout(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SCHEDULED = 'scheduled', 'Scheduled'
        PROCESSED = 'processed', 'Processed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='payouts')
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='payouts')
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    gateway_reference = models.CharField(max_length=200, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Payout {self.amount} to {self.vendor.business_name} - {self.status}'


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f'{self.user} - {self.balance} {self.currency}'

    def credit(self, amount):
        self.balance += Decimal(amount)
        self.save(update_fields=['balance', 'updated_at'])

    def debit(self, amount):
        if self.balance < Decimal(amount):
            raise ValueError('Insufficient wallet balance')
        self.balance -= Decimal(amount)
        self.save(update_fields=['balance', 'updated_at'])


class PaymentAuditLog(models.Model):
    class Action(models.TextChoices):
        PAYMENT_INITIATED = 'initiated', 'Payment Initiated'
        PAYMENT_SUCCESS = 'success', 'Payment Successful'
        PAYMENT_FAILED = 'failed', 'Payment Failed'
        REFUND_ISSUED = 'refund_issued', 'Refund Issued'
        PAYOUT_SENT = 'payout_sent', 'Payout Sent'
        WALLET_CREDITED = 'wallet_credited', 'Wallet Credited'
        WALLET_DEBITED = 'wallet_debited', 'Wallet Debited'
        INVOICE_GENERATED = 'invoice_generated', 'Invoice Generated'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='payment_audit_logs')
    action = models.CharField(max_length=30, choices=Action.choices)
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    description = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_action_display()} - {self.created_at}'


# payments/models.py
class HostPaymentAccount(models.Model):
    host = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_account',
    )
    provider = models.CharField(max_length=20, default='paystack')
    subaccount_code = models.CharField(max_length=100, blank=True, default='')
    bank_code = models.CharField(max_length=10, blank=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, default='')
    account_number = models.CharField(max_length=20, blank=True, default='')
    account_name = models.CharField(max_length=200, blank=True, default='')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.host} — {self.subaccount_code or "not connected"}'