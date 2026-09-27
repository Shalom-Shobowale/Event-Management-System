from datetime import timedelta
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Min, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from .models import (
    SubscriptionPlan, Vendor, Service, PortfolioItem, VendorReview,
    SavedVendor, VendorCategory, VendorSubscription,
)
from event.models import Event
from bookings.models import QuoteRequest
import logging
logger = logging.getLogger(__name__)


def marketplace(request):
    vendors = Vendor.objects.filter(is_active=True, is_suspended=False)

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
        vendors = vendors.filter(
            Q(business_name__icontains=search) | Q(description__icontains=search)
        )
    if city:
        vendors = vendors.filter(city__icontains=city)

    # Safe numeric coercion for price filters
    def to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    min_price_num = to_float(min_price)
    max_price_num = to_float(max_price)
    rating_num = to_float(rating)

    if min_price_num is not None:
        vendors = vendors.annotate(
            min_service_price=Min('services__price')
        ).filter(min_service_price__gte=min_price_num)
    if max_price_num is not None:
        vendors = vendors.annotate(
            min_service_price=Min('services__price')
        ).filter(min_service_price__lte=max_price_num)
    if rating_num is not None:
        vendors = vendors.filter(average_rating__gte=rating_num)

    if sort == 'price_low':
        vendors = vendors.annotate(_min=Min('services__price')).order_by('_min')
    elif sort == 'price_high':
        vendors = vendors.annotate(_min=Min('services__price')).order_by('-_min')
    elif sort == 'reviews':
        vendors = vendors.order_by('-total_reviews')
    else:
        vendors = vendors.order_by('-average_rating')

    # Annotate starting price for the card (uses same annotate name)
    vendors = vendors.annotate(starting_price=Min('services__price'))

    paginator = Paginator(vendors, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'vendors': page_obj,
        'page_obj': page_obj,
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
    vendor = get_object_or_404(Vendor, slug=slug, is_active=True, is_suspended=False)
    services = vendor.services.filter(is_active=True)
    reviews = vendor.reviews.all()[:10]

    subscription = getattr(vendor, 'subscription', None)
    limit = subscription.plan.portfolio_limit if (subscription and subscription.plan) else 8
    portfolio = vendor.portfolio.order_by('-is_featured', '-created_at')[:limit]

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

    if request.user.is_suspended:
        messages.error(request, 'Your account is suspended. You cannot create a vendor profile.')
        return redirect('dashboard')

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
            years_in_business=int(request.POST.get('years_in_business', 0) or 0),
            team_size=int(request.POST.get('team_size', 1) or 1),
        )

        if request.FILES.get('logo'):
            vendor.logo = request.FILES['logo']
        if request.FILES.get('cover'):
            vendor.cover_image = request.FILES['cover']
        vendor.save()

        trial_days = getattr(settings, 'VENDOR_TRIAL_DAYS', 30)
        pro_plan = SubscriptionPlan.objects.filter(name='Pro').first()

        if pro_plan:
            VendorSubscription.objects.create(
                vendor=vendor,
                plan=pro_plan,
                status=VendorSubscription.Status.TRIALING,
                trial_start_at=timezone.now(),
                trial_end_at=timezone.now() + timedelta(days=trial_days),
            )
        else:
            VendorSubscription.objects.create(
                vendor=vendor,
                status=VendorSubscription.Status.FREE,
            )

        messages.success(request, f'Vendor profile created! You have {trial_days} days of Pro access.')
        return redirect('vendor_dashboard')

    return render(request, 'vendors/register.html', {'categories': VendorCategory.choices})


@login_required
def subscribe_to_plan(request, plan_id):
    """Initialize a Paystack subscription for a plan."""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)

    if not hasattr(request.user, 'vendor_profile'):
        return redirect('vendor_register')

    vendor = request.user.vendor_profile

    # Ensure the Paystack Plan exists ONCE, then reuse it
    if not plan.paystack_plan_code:
        url = 'https://api.paystack.co/plan'
        headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
        payload = {
            'name': f'{plan.name} Monthly',
            'interval': 'monthly',
            'amount': int(plan.monthly_price * 100),
        }
        resp = requests.post(url, json=payload, headers=headers)
        data = resp.json()
        if not data.get('status'):
            messages.error(request, f'Could not create plan: {data.get("message", "unknown")}')
            return redirect('upgrade_plan')
        plan.paystack_plan_code = data['data']['plan_code']
        plan.save(update_fields=['paystack_plan_code'])

    # Initialize the subscription payment
    url = 'https://api.paystack.co/transaction/initialize'
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {
        'email': vendor.email,
        'amount': int(plan.monthly_price * 100),
        'plan': plan.paystack_plan_code,
        'callback_url': request.build_absolute_uri(reverse('subscription_callback')),
    }
    resp = requests.post(url, json=payload, headers=headers)
    data = resp.json()

    if not data.get('status'):
        messages.error(request, f'Payment initialization failed: {data.get("message", "unknown")}')
        return redirect('upgrade_plan')

    return redirect(data['data']['authorization_url'])


@login_required
def vendor_dashboard(request):
    if not hasattr(request.user, 'vendor_profile'):
        return redirect('vendor_register')

    vendor = request.user.vendor_profile
    services = vendor.services.all()
    recent_reviews = vendor.reviews.all()[:5]

    submitted_rfq_ids = QuoteRequest.objects.filter(
        proposals__vendor=vendor
    ).values_list('id', flat=True)

    open_rfqs = QuoteRequest.objects.filter(
        status='open'
    ).exclude(id__in=submitted_rfq_ids).order_by('-is_urgent', '-created_at')[:5]

    total_portfolio = vendor.portfolio.count()

    # Soft-limit warning
    subscription = getattr(vendor, 'subscription', None)
    plan_limit = subscription.plan.portfolio_limit if (subscription and subscription.plan) else 8
    hidden_portfolio = max(0, total_portfolio - plan_limit)

    context = {
        'vendor': vendor,
        'services': services,
        'recent_reviews': recent_reviews,
        'total_services': services.count(),
        'total_portfolio': total_portfolio,
        'hidden_portfolio': hidden_portfolio,
        'open_rfqs': open_rfqs,
        'open_rfqs_count': open_rfqs.count(),
    }
    return render(request, 'vendors/dashboard.html', context)


@login_required
def edit_vendor_profile(request):
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

        vendor.years_in_business = int(request.POST.get('years_in_business', 0) or 0)
        vendor.team_size = int(request.POST.get('team_size', 1) or 1)

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
        def to_int(v, default=0):
            try:
                return int(v)
            except (TypeError, ValueError):
                return default

        def to_decimal(v, default=0):
            try:
                from decimal import Decimal
                return Decimal(str(v)) if v else Decimal(default)
            except Exception:
                from decimal import Decimal
                return Decimal(default)

        service = Service.objects.create(
            vendor=vendor,
            name=request.POST.get('name', '').strip(),
            category=request.POST.get('category', 'other'),
            description=request.POST.get('description', '').strip(),
            price=to_decimal(request.POST.get('price', 0)),
            price_unit=request.POST.get('price_unit', 'per event'),
            duration_hours=to_int(request.POST.get('duration_hours', 4), 4),
            min_guests=to_int(request.POST.get('min_guests', 0), 0),
            max_guests=to_int(request.POST.get('max_guests', 1000), 1000),
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
    subscription = getattr(vendor, 'subscription', None)
    limit = subscription.plan.portfolio_limit if (subscription and subscription.plan) else 8

    if vendor.portfolio.count() >= limit:
        messages.warning(request, f'Your plan allows {limit} portfolio items. Upgrade to add more.')
        return redirect('upgrade_plan')

    if request.method == 'POST':
        image = request.FILES.get('image')
        if not image:
            messages.error(request, 'Please choose an image to upload.')
            return render(request, 'vendors/add_portfolio.html')

        PortfolioItem.objects.create(
            vendor=vendor,
            title=request.POST.get('title', '').strip(),
            description=request.POST.get('description', '').strip(),
            event_name=request.POST.get('event_name', '').strip(),
            image=image,
            is_featured=request.POST.get('is_featured') == 'on',
        )
        messages.success(request, 'Portfolio item added!')
        return redirect('vendor_dashboard')

    return render(request, 'vendors/add_portfolio.html')


@login_required
def submit_review(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)

    if request.method == 'POST':
        def to_int(v, default=5):
            try:
                return int(v)
            except (TypeError, ValueError):
                return default

        review, created = VendorReview.objects.get_or_create(
            vendor=vendor,
            reviewer=request.user,
            defaults={
                'rating': to_int(request.POST.get('rating', 5)),
                'professionalism': to_int(request.POST.get('professionalism', 5)),
                'quality': to_int(request.POST.get('quality', 5)),
                'communication': to_int(request.POST.get('communication', 5)),
                'timeliness': to_int(request.POST.get('timeliness', 5)),
                'title': request.POST.get('title', '').strip(),
                'comment': request.POST.get('comment', '').strip(),
            }
        )
        messages.success(request, 'Review submitted!')
        return redirect('vendor_profile', slug=vendor.slug)

    return render(request, 'vendors/review_form.html', {'vendor': vendor})


@login_required
def request_quote_vendor(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id, is_active=True, is_suspended=False)

    if hasattr(request.user, 'vendor_profile'):
        messages.error(request, 'Vendors cannot request quotes from other vendors.')
        return redirect('vendor_profile', slug=vendor.slug)

    events = Event.objects.filter(host=request.user).order_by('-date')

    if not events.exists():
        messages.warning(request, 'You need to create an event first before requesting quotes.')
        return redirect('create_event')

    if events.count() == 1:
        return redirect('create_quote_request', event_id=events.first().id)

    return render(request, 'vendors/select_event_for_quote.html', {
        'vendor': vendor,
        'events': events,
    })

@login_required
def upgrade_plan(request):
    """Show available subscription plans for the vendor to upgrade to."""
    if not hasattr(request.user, 'vendor_profile'):
        return redirect('vendor_register')

    vendor = request.user.vendor_profile
    subscription = getattr(vendor, 'subscription', None)

    # Only show plans that aren't the one they're currently on
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('monthly_price')

    context = {
        'vendor': vendor,
        'subscription': subscription,
        'plans': plans,
        'current_plan_name': subscription.plan.name if (subscription and subscription.plan) else 'Free',
    }
    return render(request, 'vendors/upgrade_plan.html', context)


@login_required
def subscription_callback(request):
    """Paystack redirects here after a successful subscription payment."""
    if not hasattr(request.user, 'vendor_profile'):
        return redirect('vendor_register')

    vendor = request.user.vendor_profile
    reference = request.GET.get('reference', '')

    if not reference:
        messages.error(request, 'Missing payment reference.')
        return redirect('upgrade_plan')

    # Verify server-side
    try:
        resp = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'},
            timeout=15,
        )
        data = resp.json()
    except requests.RequestException:
        messages.error(request, 'Could not reach payment provider. Try again.')
        return redirect('upgrade_plan')

    tx_data = data.get('data') or {}

    logger.info(
        'Paystack subscription callback: reference=%s status=%s plan=%s amount=%s',
        reference,
        tx_data.get('status'),
        tx_data.get('plan'),
        tx_data.get('amount'),
    )

    if not (data.get('status') and tx_data.get('status') == 'success'):
        messages.error(request, 'Payment was not successful.')
        return redirect('upgrade_plan')

    # Paystack returns `plan` as a plan CODE STRING, not a dict.
    # Guard against both shapes.
    plan_field = tx_data.get('plan')
    plan_code = None
    if isinstance(plan_field, dict):
        plan_code = plan_field.get('plan_code')
    elif isinstance(plan_field, str):
        plan_code = plan_field

    amount_paid = Decimal(tx_data.get('amount', 0)) / 100

    plan = None
    if plan_code:
        plan = SubscriptionPlan.objects.filter(paystack_plan_code=plan_code).first()
    if not plan:
        # Fallback: match by amount
        plan = SubscriptionPlan.objects.filter(monthly_price=amount_paid).first()

    if not plan:
        messages.warning(request, 'Payment received but no matching plan found. Contact support.')
        return redirect('vendor_dashboard')

    now = timezone.now()
    VendorSubscription.objects.update_or_create(
        vendor=vendor,
        defaults={
            'plan': plan,
            'status': VendorSubscription.Status.ACTIVE,
            'current_period_start': now,
            'current_period_end': now + timedelta(days=30),
            'paystack_subscription_code': tx_data.get('subscription_code', '') or '',
            'paystack_email_token': tx_data.get('email_token', '') or '',
        },
    )

    messages.success(request, f'Subscribed to {plan.name}! Your plan is now active.')
    return redirect('vendor_dashboard')  