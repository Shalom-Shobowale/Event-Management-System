from django.contrib import admin
from .models import Vendor, Service, PortfolioItem, VendorAvailability, VendorReview, SavedVendor

admin.site.register(Vendor)
admin.site.register(Service)
admin.site.register(PortfolioItem)
admin.site.register(VendorAvailability)
admin.site.register(VendorReview)
admin.site.register(SavedVendor)
