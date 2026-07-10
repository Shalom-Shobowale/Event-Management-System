from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Q, Min, Sum
from .models import Vendor, Service, PortfolioItem, VendorReview, SavedVendor, VendorCategory
from event.models import Event
from bookings.models import QuoteRequest


def marketplace(request):
    # Show all active vendors; verification badge displayed in template
    vendors = Vendor.objects.filter(is_active=True)

    # Filters
    category = request.GET.get('category', '')
    search = request.GET.get('search', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    rating = request.GET.get('rating', '')
    city = request.GET.get('city', '')
    sort = request.GET.get('sort', 'rating')

    if category:
        vendors = vendors.filter(categories__icontains=category)
    if search:
        vendors = vendors.filter(Q(business_name__icontains=search) | Q(description__icontains=search))
    if city:
        vendors = vendors.filter(city__icontains=city)
    if min_price:
        vendors = vendors.annotate(min_service_price=Min('services__price')).filter(min_service_price__gte=min_price)
    if max_price:
        vendors = vendors.annotate(min_service_price=Min('services__price')).filter(min_service_price__lte=max_price)
    if rating:
        vendors = vendors.filter(average_rating__gte=float(rating))

    # Sorting
    if sort == 'price_low':
        vendors = vendors.annotate(min_price=Min('services__price')).order_by('min_price')
    elif sort == 'price_high':
        vendors = vendors.annotate(min_price=Min('services__price')).order_by('-min_price')
    elif sort == 'reviews':
        vendors = vendors.order_by('-total_reviews')
    else:
        vendors = vendors.order_by('-average_rating')

    # Annotate with starting price
    vendors = vendors.annotate(starting_price=Min('services__price'))

    context = {
        'vendors': vendors[:24],
        'categories': VendorCategory.choices,
        'selected_category': category,
        'search': search,
        'min_price': min_price,
        'max_price': max_price,
        'rating': rating,
        'city': city,
        'sort': sort,
    }
    return render(request, 'vendors/marketplace.html', context)


def vendor_profile(request, slug):
    vendor = get_object_or_404(Vendor, slug=slug, is_active=True)
    services = vendor.services.filter(is_active=True)
    portfolio = vendor.portfolio.all()[:12]
    reviews = vendor.reviews.all()[:10]

    is_saved = False
    has_vendor_profile = False
    if request.user.is_authenticated:
        is_saved = SavedVendor.objects.filter(user=request.user, vendor=vendor).exists()
        has_vendor_profile = hasattr(request.user, 'vendor_profile')

    context = {
        'vendor': vendor,
        'services': services,
        'portfolio': portfolio,
        'reviews': reviews,
        'is_saved': is_saved,
        'has_vendor_profile': has_vendor_profile,
    }
    return render(request, 'vendors/profile.html', context)


@login_required
def save_vendor(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    saved, created = SavedVendor.objects.get_or_create(user=request.user, vendor=vendor)
    if not created:
        saved.delete()
        messages.success(request, f'{vendor.business_name} removed from saved vendors')
    else:
        messages.success(request, f'{vendor.business_name} saved!')
    return redirect('vendor_profile', slug=vendor.slug)


@login_required
def saved_vendors(request):
    saved = SavedVendor.objects.filter(user=request.user).select_related('vendor')
    return render(request, 'vendors/saved.html', {'saved_vendors': saved})


@login_required
def vendor_register(request):
    if hasattr(request.user, 'vendor_profile'):
        messages.info(request, 'You already have a vendor profile.')
        return redirect('vendor_dashboard')

    if request.method == 'POST':
        vendor = Vendor.objects.create(
            user=request.user,
            business_name=request.POST.get('business_name', '').strip(),
            description=request.POST.get('description', '').strip(),
            categories=request.POST.get('categories', ''),
            phone=request.POST.get('phone', '').strip(),
            email=request.POST.get('email', '').strip() or request.user.email,
            city=request.POST.get('city', '').strip(),
            state=request.POST.get('state', '').strip(),
            country=request.POST.get('country', '').strip(),
            years_in_business=int(request.POST.get('years_in_business', 0)),
            team_size=int(request.POST.get('team_size', 1)),
        )
        if request.FILES.get('logo'):
            vendor.logo = request.FILES['logo']
        if request.FILES.get('cover'):
            vendor.cover_image = request.FILES['cover']
        vendor.save()
        messages.success(request, 'Vendor profile created! You can now add services.')
        return redirect('vendor_dashboard')

    return render(request, 'vendors/register.html', {'categories': VendorCategory.choices})


@login_required
def vendor_dashboard(request):
    if not hasattr(request.user, 'vendor_profile'):
        return redirect('vendor_register')

    vendor = request.user.vendor_profile
    services = vendor.services.all()
    recent_reviews = vendor.reviews.all()[:5]

    # Open RFQs this vendor hasn't responded to yet
    submitted_rfq_ids = QuoteRequest.objects.filter(
        proposals__vendor=vendor
    ).values_list('id', flat=True)
    open_rfqs = QuoteRequest.objects.filter(
        status='open'
    ).exclude(id__in=submitted_rfq_ids).order_by('-is_urgent', '-created_at')[:5]

    context = {
        'vendor': vendor,
        'services': services,
        'recent_reviews': recent_reviews,
        'total_services': services.count(),
        'total_portfolio': vendor.portfolio.count(),
        'open_rfqs': open_rfqs,
        'open_rfqs_count': open_rfqs.count(),
    }
    return render(request, 'vendors/dashboard.html', context)


@login_required
def edit_vendor_profile(request):
    """Edit vendor profile information."""
    if not hasattr(request.user, 'vendor_profile'):
        return redirect('vendor_register')

    vendor = request.user.vendor_profile

    if request.method == 'POST':
        vendor.business_name = request.POST.get('business_name', vendor.business_name).strip()
        vendor.description = request.POST.get('description', vendor.description).strip()
        vendor.categories = request.POST.get('categories', vendor.categories)
        vendor.phone = request.POST.get('phone', vendor.phone).strip()
        vendor.email = request.POST.get('email', vendor.email).strip()
        vendor.city = request.POST.get('city', vendor.city).strip()
        vendor.state = request.POST.get('state', vendor.state).strip()
        vendor.country = request.POST.get('country', vendor.country).strip()
        vendor.website = request.POST.get('website', vendor.website).strip()
        vendor.instagram = request.POST.get('instagram', vendor.instagram).strip()
        vendor.facebook = request.POST.get('facebook', vendor.facebook).strip()
        vendor.years_in_business = int(request.POST.get('years_in_business', vendor.years_in_business))
        vendor.team_size = int(request.POST.get('team_size', vendor.team_size))

        if request.FILES.get('logo'):
            vendor.logo = request.FILES['logo']
        if request.FILES.get('cover_image'):
            vendor.cover_image = request.FILES['cover_image']

        vendor.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('vendor_dashboard')

    return render(request, 'vendors/edit_profile.html', {
        'vendor': vendor,
        'categories': VendorCategory.choices,
    })


@login_required
def add_service(request):
    if not hasattr(request.user, 'vendor_profile'):
        return redirect('vendor_register')

    vendor = request.user.vendor_profile

    if request.method == 'POST':
        service = Service.objects.create(
            vendor=vendor,
            name=request.POST.get('name', '').strip(),
            category=request.POST.get('category', 'other'),
            description=request.POST.get('description', '').strip(),
            price=request.POST.get('price', 0),
            price_unit=request.POST.get('price_unit', 'per event'),
            duration_hours=int(request.POST.get('duration_hours', 4)),
            min_guests=int(request.POST.get('min_guests', 0)),
            max_guests=int(request.POST.get('max_guests', 1000)),
            includes=request.POST.get('includes', ''),
            requirements=request.POST.get('requirements', ''),
        )
        messages.success(request, f'Service "{service.name}" added!')
        return redirect('vendor_dashboard')

    return render(request, 'vendors/add_service.html', {'categories': VendorCategory.choices})


@login_required
def add_portfolio(request):
    if not hasattr(request.user, 'vendor_profile'):
        return redirect('vendor_register')

    vendor = request.user.vendor_profile

    if request.method == 'POST':
        item = PortfolioItem.objects.create(
            vendor=vendor,
            title=request.POST.get('title', '').strip(),
            description=request.POST.get('description', '').strip(),
            event_name=request.POST.get('event_name', '').strip(),
            image=request.FILES.get('image'),
            is_featured=bool(request.POST.get('is_featured')),
        )
        messages.success(request, 'Portfolio item added!')
        return redirect('vendor_dashboard')

    return render(request, 'vendors/add_portfolio.html')


@login_required
def submit_review(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)

    if request.method == 'POST':
        review, created = VendorReview.objects.get_or_create(
            vendor=vendor,
            reviewer=request.user,
            defaults={
                'rating': int(request.POST.get('rating', 5)),
                'professionalism': int(request.POST.get('professionalism', 5)),
                'quality': int(request.POST.get('quality', 5)),
                'communication': int(request.POST.get('communication', 5)),
                'timeliness': int(request.POST.get('timeliness', 5)),
                'title': request.POST.get('title', '').strip(),
                'comment': request.POST.get('comment', '').strip(),
            }
        )
        messages.success(request, 'Review submitted!')
        return redirect('vendor_profile', slug=vendor.slug)

    return render(request, 'vendors/review_form.html', {'vendor': vendor})


@login_required
def request_quote_vendor(request, vendor_id):
    """Request a quote from a specific vendor - redirects to event selection or RFQ creation."""
    vendor = get_object_or_404(Vendor, id=vendor_id, is_active=True)

    # Prevent vendors from requesting quotes from other vendors
    if hasattr(request.user, 'vendor_profile'):
        messages.error(request, 'Vendors cannot request quotes from other vendors.')
        return redirect('vendor_profile', slug=vendor.slug)

    # Get user's events
    events = Event.objects.filter(host=request.user).order_by('-date')

    if not events.exists():
        messages.warning(request, 'You need to create an event first before requesting quotes.')
        return redirect('create_event')

    # If only one event, use it directly
    if events.count() == 1:
        return redirect('create_quote_request', event_id=events.first().id)

    # Show event selection page
    return render(request, 'vendors/select_event_for_quote.html', {
        'vendor': vendor,
        'events': events,
    })
