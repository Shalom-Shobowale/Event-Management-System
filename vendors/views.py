from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Min, Q
from .models import Vendor, Service, PortfolioItem, VendorReview, SavedVendor, VendorCategory


def marketplace(request):
    vendors = Vendor.objects.filter(is_active=True, verification_status='verified')

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
    if request.user.is_authenticated:
        is_saved = SavedVendor.objects.filter(user=request.user, vendor=vendor).exists()

    context = {
        'vendor': vendor,
        'services': services,
        'portfolio': portfolio,
        'reviews': reviews,
        'is_saved': is_saved,
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

    # Stats
    total_services = services.count()
    total_portfolio = vendor.portfolio.count()
    total_views = 0  # Track in future

    context = {
        'vendor': vendor,
        'services': services,
        'recent_reviews': recent_reviews,
        'total_services': total_services,
        'total_portfolio': total_portfolio,
    }
    return render(request, 'vendors/dashboard.html', context)


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
