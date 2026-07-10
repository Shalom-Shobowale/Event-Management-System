from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count, Q
from event.models import Event
from vendors.models import Vendor, Service, VendorCategory
from .models import QuoteRequest, Proposal, Booking


# ========== RFQ (Request for Quotation) Views ==========

@login_required
def create_quote_request(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)

    if request.method == 'POST':
        rfq = QuoteRequest.objects.create(
            event=event,
            created_by=request.user,
            title=request.POST.get('title', '').strip(),
            category=request.POST.get('category', 'other'),
            description=request.POST.get('description', '').strip(),
            budget_min=request.POST.get('budget_min', 0),
            budget_max=request.POST.get('budget_max', 0),
            required_date=request.POST.get('required_date'),
            location=request.POST.get('location', '').strip(),
            guest_count=int(request.POST.get('guest_count', 0)),
            special_requirements=request.POST.get('special_requirements', ''),
            is_urgent=bool(request.POST.get('is_urgent')),
        )
        messages.success(request, 'Quote request created! Vendors can now submit proposals.')
        return redirect('event_vendors', event_id=event.id)

    return render(request, 'bookings/create_rfq.html', {
        'event': event,
        'categories': VendorCategory.choices
    })


@login_required
def quote_request_detail(request, rfq_id):
    rfq = get_object_or_404(QuoteRequest, id=rfq_id)
    proposals = rfq.proposals.all().select_related('vendor')

    # Check if user can view
    if rfq.event.host != request.user and not hasattr(request.user, 'vendor_profile'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    return render(request, 'bookings/rfq_detail.html', {
        'rfq': rfq,
        'proposals': proposals,
    })


@login_required
def my_quote_requests(request):
    rfqs = QuoteRequest.objects.filter(event__host=request.user).select_related('event')
    return render(request, 'bookings/my_quote_requests.html', {'rfqs': rfqs})


@login_required
def browse_rfqs(request):
    """Vendors browse all open RFQs they can respond to."""
    if not hasattr(request.user, 'vendor_profile'):
        messages.error(request, 'You need a vendor account to browse quote requests.')
        return redirect('vendor_register')

    vendor = request.user.vendor_profile

    # Get open RFQs, excluding ones the vendor already submitted to
    submitted_rfq_ids = Proposal.objects.filter(vendor=vendor).values_list('quote_request_id', flat=True)
    rfqs = QuoteRequest.objects.filter(status='open').exclude(id__in=submitted_rfq_ids).select_related('event').order_by('-is_urgent', '-created_at')

    # Filter by category matching vendor's categories
    category = request.GET.get('category', '')
    search = request.GET.get('search', '')
    if category:
        rfqs = rfqs.filter(category=category)
    if search:
        rfqs = rfqs.filter(Q(title__icontains=search) | Q(description__icontains=search))

    return render(request, 'bookings/browse_rfqs.html', {
        'rfqs': rfqs,
        'vendor': vendor,
        'categories': VendorCategory.choices,
        'selected_category': category,
        'search': search,
    })


# ========== Proposal Views ==========

@login_required
def submit_proposal(request, rfq_id):
    rfq = get_object_or_404(QuoteRequest, id=rfq_id, status='open')

    if not hasattr(request.user, 'vendor_profile'):
        messages.error(request, 'Only vendors can submit proposals. Register as a vendor first.')
        return redirect('vendor_register')

    vendor = request.user.vendor_profile

    # Check vendor hasn't already submitted
    if Proposal.objects.filter(quote_request=rfq, vendor=vendor).exists():
        messages.info(request, 'You have already submitted a proposal for this quote request.')
        return redirect('vendor_proposals')

    if request.method == 'POST':
        proposal = Proposal.objects.create(
            quote_request=rfq,
            vendor=vendor,
            service_id=request.POST.get('service') or None,
            cover_letter=request.POST.get('cover_letter', '').strip(),
            proposed_price=request.POST.get('proposed_price', 0),
            includes=request.POST.get('includes', ''),
            terms=request.POST.get('terms', ''),
            estimated_duration_hours=int(request.POST.get('duration_hours', 4)),
        )
        messages.success(request, 'Proposal submitted! The event host will review it shortly.')
        return redirect('vendor_proposals')

    # Show all vendor services, not just category-filtered (category may not match exactly)
    services = vendor.services.filter(is_active=True)
    return render(request, 'bookings/submit_proposal.html', {
        'rfq': rfq,
        'vendor': vendor,
        'services': services,
    })


@login_required
def vendor_proposals(request):
    if not hasattr(request.user, 'vendor_profile'):
        return redirect('vendor_register')

    proposals = Proposal.objects.filter(vendor__user=request.user).select_related('quote_request', 'quote_request__event')
    return render(request, 'bookings/vendor_proposals.html', {'proposals': proposals})


@login_required
def accept_proposal(request, proposal_id):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    rfq = proposal.quote_request

    if rfq.event.host != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Create booking
    booking = Booking.objects.create(
        event=rfq.event,
        vendor=proposal.vendor,
        service=proposal.service,
        proposal=proposal,
        service_name=proposal.service.name if proposal.service else rfq.title,
        description=proposal.cover_letter,
        agreed_price=proposal.proposed_price,
        status=Booking.Status.PENDING,
    )

    # Update proposal and RFQ status
    proposal.status = Proposal.Status.ACCEPTED
    proposal.save()

    # Reject other proposals
    rfq.proposals.exclude(id=proposal.id).update(status=Proposal.Status.REJECTED)

    rfq.status = QuoteRequest.Status.AWARDED
    rfq.save()

    messages.success(request, f'Proposal accepted! Booking created with {proposal.vendor.business_name}.')
    return redirect('booking_detail', booking_id=booking.id)


# ========== Booking Views ==========

@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Check access
    is_host = booking.event.host == request.user
    is_vendor = hasattr(request.user, 'vendor_profile') and booking.vendor == request.user.vendor_profile

    if not is_host and not is_vendor:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    return render(request, 'bookings/booking_detail.html', {
        'booking': booking,
        'is_host': is_host,
        'is_vendor': is_vendor,
    })


@login_required
def event_bookings(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)
    bookings = event.bookings.all().select_related('vendor')
    return render(request, 'bookings/event_bookings.html', {
        'event': event,
        'bookings': bookings
    })


@login_required
def confirm_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if not hasattr(request.user, 'vendor_profile') or booking.vendor != request.user.vendor_profile:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    booking.confirm()
    messages.success(request, 'Booking confirmed!')
    return redirect('vendor_bookings')


@login_required
def complete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.event.host != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    booking.complete()
    messages.success(request, 'Booking marked as completed!')
    return redirect('booking_detail', booking_id=booking.id)


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    is_host = booking.event.host == request.user
    is_vendor = hasattr(request.user, 'vendor_profile') and booking.vendor == request.user.vendor_profile

    if not is_host and not is_vendor:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    booking.status = Booking.Status.CANCELLED
    booking.save()
    messages.success(request, 'Booking cancelled.')
    return redirect('dashboard')


@login_required
def vendor_bookings(request):
    if not hasattr(request.user, 'vendor_profile'):
        return redirect('vendor_register')

    vendor = request.user.vendor_profile
    bookings = Booking.objects.filter(vendor=vendor).select_related('event')
    return render(request, 'bookings/vendor_bookings.html', {'bookings': bookings})

