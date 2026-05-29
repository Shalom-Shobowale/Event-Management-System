import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum
from .models import Event, EventCategory, SeatArrangement, Budget, Expense
from guest.models import Guest
from ticket.models import CheckInLog
from bookings.models import Booking


def event_lists(request):
    events = Event.objects.filter(is_published=True, date__gte=timezone.now()).order_by('date')
    context = {
        'events': events
    }

    return render(request, 'core/landing.html', context)

@login_required
def create_event(request):
    if request.method == 'POST':
        event = Event.objects.create(
            host=request.user,
            name=request.POST.get('name', '').strip(),
            description=request.POST.get('description', '').strip(),
            venue=request.POST.get('venue', '').strip(),
            date=request.POST.get('date'),
            end_date=request.POST.get('end_date') or None,
            category=request.POST.get('category', 'other'),
            max_capacity=int(request.POST.get('max_capacity', 100)),
            seat_arrangement=request.POST.get('seat_arrangement', 'general'),
            vip_support=bool(request.POST.get('vip_support')),
            is_published=bool(request.POST.get('is_published')),
        )
        if not event.slug:
            event.slug = f"{event.name.lower().replace(' ', '-')[:50]}-{event.id.hex[:8]}"
            event.save()
        if request.FILES.get('banner'):
            event.banner = request.FILES['banner']
            event.save()
        messages.success(request, f'Event "{event.name}" created successfully!')
        return redirect('event_dashboard', event_id=event.id)

    context = {
        'categories': EventCategory.choices,
        'arrangements': SeatArrangement.choices,
    }
    return render(request, 'events/create.html', context)


@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)
    if request.method == 'POST':
        event.name = request.POST.get('name', '').strip()
        event.description = request.POST.get('description', '').strip()
        event.venue = request.POST.get('venue', '').strip()
        event.date = request.POST.get('date')
        event.end_date = request.POST.get('end_date') or None
        event.category = request.POST.get('category', 'other')
        event.max_capacity = int(request.POST.get('max_capacity', 100))
        event.seat_arrangement = request.POST.get('seat_arrangement', 'general')
        event.vip_support = bool(request.POST.get('vip_support'))
        event.is_published = bool(request.POST.get('is_published'))
        if request.FILES.get('banner'):
            event.banner = request.FILES['banner']
        event.save()
        messages.success(request, 'Event updated successfully.')
        return redirect('event_dashboard', event_id=event.id)

    context = {
        'event': event,
        'categories': EventCategory.choices,
        'arrangements': SeatArrangement.choices,
    }
    return render(request, 'events/edit.html', context)


@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)
    if request.method == 'POST':
        name = event.name
        event.delete()
        messages.success(request, f'Event "{name}" deleted.')
        return redirect('dashboard')
    return render(request, 'events/delete_confirm.html', {'event': event})


@login_required
def event_dashboard(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)
    guests = event.guests.all()
    check_ins = CheckInLog.objects.filter(guest__event=event)

    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    if search:
        guests = guests.filter(full_name__icontains=search) | guests.filter(email__icontains=search)
    if status == 'checked_in':
        guests = guests.filter(checked_in=True)
    elif status == 'not_checked_in':
        guests = guests.filter(checked_in=False)

    context = {
        'event': event,
        'guests': guests,
        'total_check_ins': check_ins.count(),
        'valid_check_ins': check_ins.filter(status='valid').count(),
        'duplicate_check_ins': check_ins.filter(status='duplicate').count(),
        'invalid_check_ins': check_ins.filter(status='invalid').count(),
        'bookings': event.bookings.all(),
    }
    return render(request, 'events/dashboard.html', context)


@login_required
def export_guests(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)
    guests = event.guests.all()
    lines = ['Name,Email,Phone,Seat,Checked In,Registered At']
    for g in guests:
        lines.append(f'"{g.full_name}","{g.email}","{g.phone}","{g.seat_number}","{g.checked_in}","{g.registered_at}"')
    import csv
    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{event.name}_guests.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Email', 'Phone', 'Seat', 'Checked In', 'Registered At'])
    for g in guests:
        writer.writerow([g.full_name, g.email, g.phone, g.seat_number, g.checked_in, g.registered_at])
    return response


@login_required
def analytics(request):
    user = request.user
    events = Event.objects.filter(host=user)
    all_guests = Guest.objects.filter(event__host=user)
    all_checkins = CheckInLog.objects.filter(guest__event__host=user)

    event_data = []
    for event in events:
        event_data.append({
            'name': event.name,
            'registered': event.registered_guests,
            'checked_in': event.checked_in_guests,
            'rate': event.attendance_rate,
        })

    hourly_data = {}
    for ci in all_checkins.filter(status='valid'):
        hour = ci.scanned_at.strftime('%H:00') if ci.scanned_at else ''
        hourly_data[hour] = hourly_data.get(hour, 0) + 1

    context = {
        'total_events': events.count(),
        'total_guests': all_guests.count(),
        'total_checked_in': all_guests.filter(checked_in=True).count(),
        'no_show_rate': round(
            ((all_guests.count() - all_guests.filter(checked_in=True).count()) / all_guests.count() * 100)
            if all_guests.count() > 0 else 0, 1
        ),
        'total_scans': all_checkins.count(),
        'event_data_json': json.dumps(event_data),
        'hourly_data_json': json.dumps(hourly_data),
        'events': events,
    }
    return render(request, 'analytics.html', context)


# ========== BUDGET VIEWS ==========

@login_required
def event_budget(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)
    budget, created = Budget.objects.get_or_create(event=event)
    expenses = event.expenses.all().order_by('-created_at')

    # Category breakdown
    category_totals = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')

    context = {
        'event': event,
        'budget': budget,
        'expenses': expenses,
        'category_totals': category_totals,
    }
    return render(request, 'events/budget.html', context)


@login_required
def update_budget(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)
    budget, created = Budget.objects.get_or_create(event=event)

    if request.method == 'POST':
        budget.total_budget = request.POST.get('total_budget', budget.total_budget)
        budget.currency = request.POST.get('currency', 'USD')
        budget.notes = request.POST.get('notes', budget.notes)
        budget.save()
        messages.success(request, 'Budget updated!')
        return redirect('event_budget', event_id=event.id)

    return render(request, 'events/update_budget.html', {'event': event, 'budget': budget})


@login_required
def add_expense(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)

    if request.method == 'POST':
        expense = Expense.objects.create(
            event=event,
            title=request.POST.get('title', '').strip(),
            category=request.POST.get('category', 'misc'),
            amount=request.POST.get('amount', 0),
            description=request.POST.get('description', ''),
            paid=bool(request.POST.get('paid')),
            vendor_name=request.POST.get('vendor_name', '').strip(),
            created_by=request.user,
        )
        if request.FILES.get('receipt'):
            expense.receipt = request.FILES['receipt']
            expense.save()
        messages.success(request, f'Expense "{expense.title}" added!')
        return redirect('event_budget', event_id=event.id)

    return render(request, 'events/add_expense.html', {
        'event': event,
        'categories': Expense.Category.choices
    })


@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)

    if expense.event.host != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        expense.title = request.POST.get('title', expense.title)
        expense.category = request.POST.get('category', expense.category)
        expense.amount = request.POST.get('amount', expense.amount)
        expense.description = request.POST.get('description', expense.description)
        expense.paid = bool(request.POST.get('paid'))
        expense.vendor_name = request.POST.get('vendor_name', expense.vendor_name)
        if request.FILES.get('receipt'):
            expense.receipt = request.FILES['receipt']
        expense.save()
        messages.success(request, 'Expense updated!')
        return redirect('event_budget', event_id=expense.event.id)

    return render(request, 'events/edit_expense.html', {
        'expense': expense,
        'categories': Expense.Category.choices
    })
