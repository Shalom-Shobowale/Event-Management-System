from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from event.models import Event
from .models import Task, Conversation, Message, EventMember, EventFile, EventNote, ActivityLog


# ========== Task Management ==========

@login_required
def event_tasks(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)
    tasks = event.tasks.all()

    # Filter
    status = request.GET.get('status', '')
    priority = request.GET.get('priority', '')
    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)

    # Stats
    total = tasks.count()
    done = tasks.filter(status='done').count()
    progress = round((done / total * 100) if total > 0 else 0)

    return render(request, 'collaboration/tasks.html', {
        'event': event,
        'tasks': tasks,
        'total': total,
        'done': done,
        'progress': progress,
    })


@login_required
def create_task(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)

    if request.method == 'POST':
        task = Task.objects.create(
            event=event,
            title=request.POST.get('title', '').strip(),
            description=request.POST.get('description', ''),
            priority=request.POST.get('priority', 'medium'),
            status=request.POST.get('status', 'todo'),
            due_date=request.POST.get('due_date') or None,
            assignee_id=request.POST.get('assignee') or None,
            created_by=request.user,
        )
        messages.success(request, f'Task "{task.title}" created!')

        # Log activity
        ActivityLog.objects.create(
            event=event,
            user=request.user,
            action='task_created',
            description=f'Created task: {task.title}',
        )

        return redirect('event_tasks', event_id=event.id)

    return render(request, 'collaboration/create_task.html', {'event': event})


@login_required
def update_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if task.event.host != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        task.title = request.POST.get('title', task.title)
        task.description = request.POST.get('description', task.description)
        task.priority = request.POST.get('priority', task.priority)
        task.status = request.POST.get('status', task.status)
        if request.POST.get('due_date'):
            task.due_date = request.POST.get('due_date')
        task.save()
        messages.success(request, 'Task updated!')
        return redirect('event_tasks', event_id=task.event.id)

    return render(request, 'collaboration/update_task.html', {'task': task})


@login_required
def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if task.event.host != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    task.mark_done(request.user)
    messages.success(request, f'Task "{task.title}" completed!')

    ActivityLog.objects.create(
        event=task.event,
        user=request.user,
        action='task_completed',
        description=f'Completed task: {task.title}',
    )

    return redirect('event_tasks', event_id=task.event.id)


# ========== Messaging ==========

@login_required
def conversations(request):
    convos = Conversation.objects.filter(participants=request.user)
    return render(request, 'collaboration/conversations.html', {'conversations': convos})


@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    messages = conversation.messages.all()

    # Mark as read
    for msg in messages:
        if not msg.is_read_by(request.user) and msg.sender != request.user:
            msg.mark_read(request.user)

    if request.method == 'POST':
        msg = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=request.POST.get('content', '').strip(),
        )
        if request.FILES.get('attachment'):
            msg.attachment = request.FILES['attachment']
            msg.save()
        return redirect('conversation_detail', conversation_id=conversation.id)

    return render(request, 'collaboration/conversation.html', {
        'conversation': conversation,
        'messages': messages,
    })


@login_required
def start_conversation(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if event.host != request.user and not hasattr(request.user, 'vendor_profile'):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        participant_id = request.POST.get('participant')
        if not participant_id:
            messages.error(request, 'Please select a participant.')
            return redirect('event_dashboard', event_id=event.id)

        conversation, created = Conversation.objects.get_or_create(
            event=event,
            subject=request.POST.get('subject', f'{event.name} Discussion'),
        )
        conversation.participants.add(request.user.id, participant_id)

        if request.POST.get('message'):
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=request.POST.get('message', '').strip(),
            )

        return redirect('conversation_detail', conversation_id=conversation.id)

    # Get potential participants
    participants = [request.user]
    if event.host != request.user:
        participants.append(event.host)
    for booking in event.bookings.filter(status='confirmed'):
        if booking.vendor.user not in participants:
            participants.append(booking.vendor.user)

    return render(request, 'collaboration/start_conversation.html', {
        'event': event,
        'potential_participants': participants,
    })


# ========== Event Collaboration ==========

@login_required
def event_workspace(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)
    tasks = event.tasks.all()
    notes = event.notes.all()[:5]
    files = event.files.all()[:10]
    activity = event.activity_log.all()[:20]
    members = event.members.all()

    # Stats
    task_stats = {
        'total': tasks.count(),
        'done': tasks.filter(status='done').count(),
        'progress': round((tasks.filter(status='done').count() / tasks.count() * 100) if tasks.count() > 0 else 0)
    }

    return render(request, 'collaboration/workspace.html', {
        'event': event,
        'tasks': tasks,
        'notes': notes,
        'files': files,
        'activity': activity,
        'members': members,
        'task_stats': task_stats,
    })


@login_required
def add_note(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)

    if request.method == 'POST':
        note = EventNote.objects.create(
            event=event,
            author=request.user,
            title=request.POST.get('title', '').strip(),
            content=request.POST.get('content', '').strip(),
        )
        messages.success(request, 'Note added!')
        return redirect('event_workspace', event_id=event.id)

    return render(request, 'collaboration/add_note.html', {'event': event})


@login_required
def upload_file(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)

    if request.method == 'POST':
        file = request.FILES.get('file')
        if file:
            EventFile.objects.create(
                event=event,
                uploaded_by=request.user,
                file=file,
                name=file.name,
                description=request.POST.get('description', ''),
            )
            messages.success(request, 'File uploaded!')
        return redirect('event_workspace', event_id=event.id)

    return render(request, 'collaboration/upload_file.html', {'event': event})


@login_required
def add_member(request, event_id):
    event = get_object_or_404(Event, id=event_id, host=request.user)

    if request.method == 'POST':
        user_id = request.POST.get('user')
        role = request.POST.get('role', 'viewer')

        member, created = EventMember.objects.get_or_create(
            event=event,
            user_id=user_id,
            defaults={'role': role, 'invited_by': request.user}
        )
        if created:
            messages.success(request, 'Member added!')
        else:
            messages.info(request, 'Member already exists.')
        return redirect('event_workspace', event_id=event.id)

    return render(request, 'collaboration/add_member.html', {'event': event})
