from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from guest.models import Guest
from .models import CheckInLog


def validate_ticket(request, ticket_code):
    try:
        guest = Guest.objects.get(ticket_code=ticket_code)
    except Guest.DoesNotExist:
        return render(request, 'tickets/invalid.html', {'status': 'invalid'})

    if guest.checked_in:
        CheckInLog.objects.create(
            guest=guest,
            status=CheckInLog.Status.DUPLICATE,
        )
        return render(request, 'tickets/duplicate.html', {
            'guest': guest,
            'status': 'duplicate',
        })

    guest.check_in()
    CheckInLog.objects.create(
        guest=guest,
        status=CheckInLog.Status.VALID,
    )
    return render(request, 'tickets/valid.html', {
        'guest': guest,
        'status': 'valid',
    })


@login_required
def scanner(request):
    return render(request, 'tickets/scanner.html')


@login_required
def api_validate(request, ticket_code):
    try:
        guest = Guest.objects.get(ticket_code=ticket_code)
    except Guest.DoesNotExist:
        return JsonResponse({'status': 'invalid', 'message': 'Ticket not found'}, status=404)

    if guest.checked_in:
        CheckInLog.objects.create(
            guest=guest,
            status=CheckInLog.Status.DUPLICATE,
            scanned_by=request.user,
        )
        return JsonResponse({
            'status': 'duplicate',
            'message': 'Already checked in',
            'guest': {
                'name': guest.full_name,
                'event': guest.event.name,
                'seat': guest.seat_number,
                'checked_in_at': guest.checked_in_at.isoformat() if guest.checked_in_at else None,
            }
        })

    guest.check_in()
    CheckInLog.objects.create(
        guest=guest,
        status=CheckInLog.Status.VALID,
        scanned_by=request.user,
    )
    return JsonResponse({
        'status': 'valid',
        'message': 'Check-in successful',
        'guest': {
            'name': guest.full_name,
            'event': guest.event.name,
            'seat': guest.seat_number,
            'checked_in_at': guest.checked_in_at.isoformat() if guest.checked_in_at else None,
        }
    })
