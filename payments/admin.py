from django.contrib import admin
from .models import Transaction, Invoice, Refund, VendorPayout, Wallet, PaymentAuditLog


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'transaction_type', 'status', 'amount', 'gateway', 'created_at')
    list_filter = ('status', 'transaction_type', 'gateway')
    search_fields = ('reference', 'gateway_reference', 'user__username')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'booking', 'vendor', 'total', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('invoice_number',)


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'amount', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(VendorPayout)
class VendorPayoutAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'amount', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'currency', 'is_active')


@admin.register(PaymentAuditLog)
class PaymentAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'actor', 'transaction', 'created_at')
    list_filter = ('action',)
