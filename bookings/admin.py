from django.contrib import admin
from .models import QuoteRequest, Proposal, Booking

admin.site.register(QuoteRequest)
admin.site.register(Proposal)
admin.site.register(Booking)
