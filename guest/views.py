from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Guest
from event.models import Event


def guest_register(request, event_id):
    event = get_object_or_404(Event, id=event_id, is_published=True)

    if event.is_full:
        return render(request, 'guests/full.html', {'event': event})

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        meal_preference = request.POST.get('meal_preference', '').strip()
        plus_one = bool(request.POST.get('plus_one'))
        notes = request.POST.get('notes', '').strip()

        if not all([full_name, email]):
            messages.error(request, 'Name and email are required.')
            return render(request, 'guests/register.html', {'event': event})

        if Guest.objects.filter(event=event, email=email).exists():
            messages.error(request, 'This email is already registered for this event.')
            return render(request, 'guests/register.html', {'event': event})

        guest = Guest.objects.create(
            event=event,
            full_name=full_name,
            email=email,
            phone=phone,
            meal_preference=meal_preference,
            plus_one=plus_one,
            notes=notes,
        )
        messages.success(request, 'Registration successful! Your ticket is ready.')
        return redirect('guest_ticket', guest_id=guest.id)

    return render(request, 'guests/register.html', {'event': event})


def guest_ticket(request, guest_id):
    guest = get_object_or_404(Guest, id=guest_id)
    return render(request, 'guests/ticket.html', {'guest': guest})
