import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Sum, Q
from .models import Event, EventCategory, SeatArrangement, Budget, Expense
from guest.models import Guest
from ticket.models import CheckInLog
from bookings.models import Booking 
import re
from .models import Seat
from django.db import transaction

from decimal import Decimal, InvalidOperation

@login_required
def create_event(request):
    if request.user.is_suspended:
        messages.error(request, 'Your account is suspended. You cannot create events.')
        return redirect('dashboard')

    if request.method == 'POST':
        # Safely parse price
        price_raw = request.POST.get('price', '').strip()
        price = None
        if price_raw:
            try:
                price = Decimal(price_raw)
                if price < 0:
                    price = None
            except (InvalidOperation, ValueError):
                price = None

        # If price set, host must have a connected bank account
        if price and not request.user.host_subaccount_code:
            messages.error(
                request,
                'Connect a bank account before creating a paid event.'
            )
            return redirect('connect_bank_account')

        event = Event.objects.create(
            host=request.user,
            name=request.POST.get('name', '').strip(),
            description=request.POST.get('description', '').strip(),
            venue=request.POST.get('venue', '').strip(),
            date=request.POST.get('date'),
            end_date=request.POST.get('end_date') or None,
            category=request.POST.get('category', 'other'),
            max_capacity=int(request.POST.get('max_capacity', 100) or 100),
            seat_arrangement=request.POST.get('seat_arrangement', 'general'),
            vip_support=bool(request.POST.get('vip_support')),
            is_published=bool(request.POST.get('is_published')),
            price=price,
            host_subaccount_code=request.user.host_subaccount_code or '',
        )

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
        # Parse price safely
        price_raw = request.POST.get('price', '').strip()
        price = None
        if price_raw:
            try:
                p = Decimal(price_raw)
                if p > 0:
                    price = p
            except (InvalidOperation, ValueError):
                price = None

        # Paid events require a connected bank account
        if price and not request.user.host_subaccount_code:
            messages.error(
                request,
                'Connect a bank account before setting a ticket price.'
            )
            return redirect('connect_bank_account')

        event.name = request.POST.get('name', '').strip()
        event.description = request.POST.get('description', '').strip()
        event.venue = request.POST.get('venue', '').strip()
        event.date = request.POST.get('date')
        event.end_date = request.POST.get('end_date') or None
        event.category = request.POST.get('category', 'other')
        event.max_capacity = int(request.POST.get('max_capacity', 100) or 100)
        event.seat_arrangement = request.POST.get('seat_arrangement', 'general')
        event.vip_support = bool(request.POST.get('vip_support'))
        event.is_published = bool(request.POST.get('is_published'))
        event.price = price
        event.host_subaccount_code = request.user.host_subaccount_code or ''

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
        # Never hard-delete if there are guests or payments
        has_guests = event.guests.exists()
        has_payments = event.guests.filter(payment_status='paid').exists()

        if has_payments:
            # Archive instead — never destroy financial records
            event.is_archived = True
            event.save(update_fields=['is_archived'])
            messages.success(request, f'"{event.name}" has been archived. Payment records are preserved.')
        elif has_guests:
            # Warn and archive — guests may want their tickets
            event.is_archived = True
            event.save(update_fields=['is_archived'])
            messages.success(request, f'"{event.name}" has been archived. Guest records are preserved.')
        else:
            # Safe to delete — no guests, no payments
            name = event.name
            event.delete()
            messages.success(request, f'"{name}" has been deleted.')

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

    paginator = Paginator(guests, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

        # Total earnings from PAID guests at this event
    paid_earnings = event.guests.filter(
        payment_status='paid'
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

    # Optional: how many guests actually paid
    paid_guest_count = event.guests.filter(payment_status='paid').count()

    context = {
        'event': event,
        'guests': page_obj,
        'page_obj': page_obj,
        'total_check_ins': check_ins.count(),
        'valid_check_ins': check_ins.filter(status='valid').count(),
        'duplicate_check_ins': check_ins.filter(status='duplicate').count(),
        'invalid_check_ins': check_ins.filter(status='invalid').count(),
        'bookings': event.bookings.all(),
        'paid_earnings': paid_earnings,
        'paid_guest_count': paid_guest_count,
    }
    return render(request, 'events/dashboard.html', context)



def event_public(request, event_id):
    """
    Public event page. No login. Serves anyone with the URL.

    Excludes suspended and archived events (404). Shows everything
    a guest needs to decide whether to register.
    """
    event = get_object_or_404(
        Event.objects.select_related('host'),
        id=event_id,
        is_suspended=False,
        is_archived=False,
    )
    return render(request, 'events/public.html', {
        'event': event,
        'registered_count': event.registered_guests,
        'is_full': event.registered_guests >= event.max_capacity,
    })

@login_required
def event_list(request):
    """
    Host's events, tabbed: upcoming / past / archived.

    Production notes:
    - Only the host's own events (no auth leak)
    - Counts computed per tab (single query each)
    - Paginated at 24 (8 rows × 3 cols)
    - Uses Event.Meta.indexes on (host, -date)
    """
    from django.utils import timezone

    tab = request.GET.get('tab', 'upcoming')
    if tab not in ('upcoming', 'past', 'archived'):
        tab = 'upcoming'

    now = timezone.now()

    # Base: this host's events only
    base = Event.objects.filter(host=request.user)

    # Tab-specific queryset
    if tab == 'upcoming':
        events_qs = base.filter(
            date__gte=now,
            is_archived=False,
        ).order_by('date')          # soonest first
    elif tab == 'past':
        events_qs = base.filter(
            date__lt=now,
            is_archived=False,
        ).order_by('-date')         # most recent first
    else:  # archived
        events_qs = base.filter(
            is_archived=True,
        ).order_by('-date')

    # Counts for the tabs (3 quick queries, all indexed)
    upcoming_count = base.filter(date__gte=now, is_archived=False).count()
    past_count = base.filter(date__lt=now, is_archived=False).count()
    archived_count = base.filter(is_archived=True).count()

    paginator = Paginator(events_qs, 24)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'events/list.html', {
        'page_obj': page_obj,
        'paginator': paginator,
        'tab': tab,
        'upcoming_count': upcoming_count,
        'past_count': past_count,
        'archived_count': archived_count,
    })


@login_required
def event_archive(request, event_id):
    """
    Archive an event. POST-only.

    Archiving hides the event from the public site but keeps it in the
    host's records. Reversible via event_unarchive.
    """
    if request.method != 'POST':
        return redirect('event_list')

    event = get_object_or_404(Event, id=event_id, host=request.user)

    if event.is_archived:
        messages.info(request, f'"{event.name}" is already archived.')
        return redirect('event_list')

    event.is_archived = True
    event.save(update_fields=['is_archived'])

    messages.success(
        request,
        f'"{event.name}" archived. It is now hidden from the public site.'
    )
    return redirect('event_list')


@login_required
def event_unarchive(request, event_id):
    """Restore an archived event. POST-only."""
    if request.method != 'POST':
        return redirect('event_list')

    event = get_object_or_404(Event, id=event_id, host=request.user)

    if not event.is_archived:
        messages.info(request, f'"{event.name}" is not archived.')
        return redirect('event_list')

    event.is_archived = False
    event.save(update_fields=['is_archived'])

    messages.success(
        request,
        f'"{event.name}" is back on the public site.'
    )
    return redirect('event_list')


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


def event_browse(request):
    """
    Public catalog of all upcoming events. No login required.
    Supports category filter and pagination.
    """
    from django.utils import timezone
    from .models import Event, EventCategory

    events_qs = (
        Event.objects
        .select_related('host')
        .filter(
            is_published=True,
            is_archived=False,
            is_suspended=False,
            date__gte=timezone.now(),
        )
        .order_by('date')
    )

    # Optional category filter
    category = request.GET.get('category', '').strip()
    if category and category in dict(EventCategory.choices):
        events_qs = events_qs.filter(category=category)

    # Optional search
    search = request.GET.get('q', '').strip()
    if search:
        events_qs = events_qs.filter(
            Q(name__icontains=search) |
            Q(venue__icontains=search) |
            Q(description__icontains=search)
        )

    paginator = Paginator(events_qs, 12)   # 12 per page — fits 3-col grid at 4 rows
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'events/browse.html', {
        'page_obj': page_obj,
        'paginator': paginator,
        'category': category,
        'search': search,
        'categories': EventCategory.choices,
        'total_count': paginator.count,
    })


# ==================== SEATING ====================

def _parse_row_labels(spec):
    """
    Parse a row spec like 'A-J' into ['A', 'B', ..., 'J'].
    Supports single letters, ranges, and comma-separated combos:
      'A-J'         -> A..J
      'A,B,C'       -> A, B, C
      'A-C,E,F-H'   -> A, B, C, E, F, G, H
    """
    result = []
    for part in spec.split(','):
        part = part.strip().upper()
        if not part:
            continue
        if '-' in part:
            start, end = part.split('-', 1)
            if len(start) == 1 and len(end) == 1:
                for c in range(ord(start), ord(end) + 1):
                    result.append(chr(c))
            else:
                # multi-letter range — fallback to literal
                result.append(part)
        else:
            result.append(part)
    return result


@login_required
def event_seats(request, event_id):
    """Host-facing seat management page."""
    event = get_object_or_404(Event, id=event_id, host=request.user)

    seats = event.seats.select_related('guest').order_by('sort_order', 'label')

    # Group by section for display
    sections = {}
    for seat in seats:
        s = seat.section or 'General'
        sections.setdefault(s, []).append(seat)

    # Counts
    total = seats.count()
    available = seats.filter(status='available').count()
    held = seats.filter(status='held').count()
    taken = seats.filter(status='taken').count()
    blocked = seats.filter(status='blocked').count()

    # Guests without a seat (for the assign dropdown)
    unseated_guests = event.guests.filter(assigned_seat__isnull=True).order_by('full_name')

    context = {
        'event': event,
        'seats': seats,
        'sections': sections,
        'total_seats': total,
        'available_count': available,
        'held_count': held,
        'taken_count': taken,
        'blocked_count': blocked,
        'unseated_guests': unseated_guests,
    }
    return render(request, 'events/seats.html', context)


@login_required
@transaction.atomic
def event_seats_generate(request, event_id):
    """
    Create a block of seats for an event.
    POST params:
      row_spec        e.g. 'A-J'
      seats_per_row   e.g. 20
      start_number    e.g. 1
      section         optional, e.g. 'Family'
    """
    event = get_object_or_404(Event, id=event_id, host=request.user)

    if request.method != 'POST':
        return redirect('event_seats', event_id=event.id)

    row_spec = request.POST.get('row_spec', '').strip().upper()
    try:
        seats_per_row = int(request.POST.get('seats_per_row', 0))
    except (ValueError, TypeError):
        seats_per_row = 0
    try:
        start_number = int(request.POST.get('start_number', 1))
    except (ValueError, TypeError):
        start_number = 1
    section = request.POST.get('section', '').strip()

    rows = _parse_row_labels(row_spec)

    if not rows or seats_per_row < 1:
        messages.error(request, 'Enter a valid row range and seats per row.')
        return redirect('event_seats', event_id=event.id)

    # Guard: don't create duplicates (unique constraint on event+label would
    # fail mid-loop otherwise)
    existing_labels = set(
        Seat.objects.filter(event=event).values_list('label', flat=True)
    )

    created = 0
    skipped = 0
    seat_objects = []
    order = 0

    for row in rows:
        for n in range(start_number, start_number + seats_per_row):
            label = f'{row}-{n}'
            if label in existing_labels:
                skipped += 1
                continue
            seat_objects.append(Seat(
                event=event,
                label=label,
                section=section,
                status=Seat.Status.AVAILABLE,
                sort_order=order,
            ))
            order += 1
            created += 1

    if seat_objects:
        Seat.objects.bulk_create(seat_objects, batch_size=500)

    messages.success(
        request,
        f'Created {created} seat{"s" if created != 1 else ""}.'
        + (f' Skipped {skipped} duplicate label{"s" if skipped != 1 else ""}.' if skipped else '')
    )
    return redirect('event_seats', event_id=event.id)


@login_required
@transaction.atomic
def event_seat_hold(request, event_id):
    """
    Bulk-hold a range of seats.
    POST params:
      from_label     e.g. 'A-1'
      to_label       e.g. 'A-8'
      held_for       e.g. "Bride's family"
      held_note      optional
    Only 'available' seats are affected. Taken seats are left alone.
    """
    event = get_object_or_404(Event, id=event_id, host=request.user)

    if request.method != 'POST':
        return redirect('event_seats', event_id=event.id)

    from_label = request.POST.get('from_label', '').strip()
    to_label = request.POST.get('to_label', '').strip()
    held_for = request.POST.get('held_for', '').strip()
    held_note = request.POST.get('held_note', '').strip()
    access_code = request.POST.get('access_code', '').strip()

    if not (from_label and to_label and held_for):
        messages.error(request, 'From, to, and "held for" are required.')
        return redirect('event_seats', event_id=event.id)

    # Fetch all seats in event, ordered by sort_order
    seats = list(
        Seat.objects.filter(event=event).order_by('sort_order', 'label')
    )

    # Find indices of the boundary labels
    labels = [s.label for s in seats]
    try:
        start_idx = labels.index(from_label)
        end_idx = labels.index(to_label)
    except ValueError:
        messages.error(request, 'One or both of those seat labels do not exist.')
        return redirect('event_seats', event_id=event.id)

    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    to_hold = [
        s for s in seats[start_idx:end_idx + 1]
        if s.status == Seat.Status.AVAILABLE
    ]

    count = 0
    for seat in to_hold:
        seat.status = Seat.Status.HELD
        seat.held_for = held_for
        seat.held_note = held_note
        seat.access_code = access_code
        seat.save(update_fields=['status', 'held_for', 'held_note', 'access_code', 'updated_at'])
        count += 1

    messages.success(request, f'Held {count} seat{"s" if count != 1 else ""} for "{held_for}".')
    return redirect('event_seats', event_id=event.id)


@login_required
@transaction.atomic
def event_seat_release(request, event_id):
    """Release a range of held seats back to 'available'."""
    event = get_object_or_404(Event, id=event_id, host=request.user)

    if request.method != 'POST':
        return redirect('event_seats', event_id=event.id)

    from_label = request.POST.get('from_label', '').strip()
    to_label = request.POST.get('to_label', '').strip()

    if not (from_label and to_label):
        messages.error(request, 'From and to labels are required.')
        return redirect('event_seats', event_id=event.id)

    seats = list(
        Seat.objects.filter(event=event).order_by('sort_order', 'label')
    )
    labels = [s.label for s in seats]
    try:
        start_idx = labels.index(from_label)
        end_idx = labels.index(to_label)
    except ValueError:
        messages.error(request, 'One or both of those seat labels do not exist.')
        return redirect('event_seats', event_id=event.id)

    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    released = 0
    for seat in seats[start_idx:end_idx + 1]:
        if seat.status == Seat.Status.HELD:
            seat.status = Seat.Status.AVAILABLE
            seat.held_for = ''
            seat.held_note = ''
            seat.access_code = ''
            seat.save(update_fields=['status', 'held_for', 'held_note', 'access_code', 'updated_at'])
            released += 1

    messages.success(request, f'Released {released} seat{"s" if released != 1 else ""}.')
    return redirect('event_seats', event_id=event.id)


@login_required
@transaction.atomic
def event_seat_assign(request, event_id, seat_id):
    """
    Assign a guest to a seat.
    POST params:
      guest_id
    Works whether the seat is 'held' or 'available'. If already 'taken', it
    rejects (you must unassign first).
    """
    event = get_object_or_404(Event, id=event_id, host=request.user)
    seat = get_object_or_404(Seat, id=seat_id, event=event)

    if request.method != 'POST':
        return redirect('event_seats', event_id=event.id)

    guest_id = request.POST.get('guest_id')
    guest = get_object_or_404(Guest, id=guest_id, event=event)

    if seat.guest_id is not None:
        messages.error(request, 'That seat is already assigned. Unassign it first.')
        return redirect('event_seats', event_id=event.id)

    if hasattr(guest, 'assigned_seat') and guest.assigned_seat:
        # Guest already has a different seat — move them
        old_seat = guest.assigned_seat
        old_seat.guest = None
        old_seat.status = Seat.Status.AVAILABLE
        old_seat.held_for = ''
        old_seat.save(update_fields=['guest', 'status', 'held_for', 'updated_at'])

    seat.guest = guest
    seat.status = Seat.Status.TAKEN
    seat.held_for = ''  # clear any hold reason
    seat.save(update_fields=['guest', 'status', 'held_for', 'updated_at'])

    # Keep the guest's seat_number field in sync for the ticket
    guest.seat_number = seat.label
    guest.save(update_fields=['seat_number'])

    messages.success(request, f'Assigned {guest.full_name} to seat {seat.label}.')
    return redirect('event_seats', event_id=event.id)


@login_required
@transaction.atomic
def event_seat_unassign(request, event_id, seat_id):
    """Detach whatever guest is on this seat, making it available again."""
    event = get_object_or_404(Event, id=event_id, host=request.user)
    seat = get_object_or_404(Seat, id=seat_id, event=event)

    if request.method != 'POST':
        return redirect('event_seats', event_id=event.id)

    guest = seat.guest
    if guest:
        guest.seat_number = ''
        guest.save(update_fields=['seat_number'])

    seat.guest = None
    seat.status = Seat.Status.AVAILABLE
    seat.save(update_fields=['guest', 'status', 'updated_at'])

    messages.success(request, f'Seat {seat.label} is now available.')
    return redirect('event_seats', event_id=event.id)


@login_required
def event_seats_search_guests(request, event_id):
    """AJAX: search guests in this event by name or email."""
    event = get_object_or_404(Event, id=event_id, host=request.user)

    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    guests = (
        event.guests
        .filter(Q(full_name__icontains=q) | Q(email__icontains=q))
        .order_by('full_name')[:20]
    )
    results = [
        {
            'id': str(g.id),
            'name': g.full_name,
            'email': g.email,
            'current_seat': g.seat_number or '',
        }
        for g in guests
    ]
    return JsonResponse({'results': results})