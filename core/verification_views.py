from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from core.verification_models import EmailVerification, PhoneVerification, VendorDocument, UserNotification
from core.emails import send_verification_email


@login_required
def send_email_verification(request):
    """
    Generate a new email verification code and send it to the user.

    The code is delivered by email only — never shown in the UI.
    """
    ev = EmailVerification.create_for(request.user)

    # Send — helper logs failures but never raises
    send_verification_email(user=request.user, code=ev.code)

    # NEVER show the code in the flash message.
    messages.success(
        request,
        f'A 6-digit verification code has been sent to {request.user.email}. '
        f'Check your inbox (and spam folder).'
    )
    # Redirect to the entry page so the user has somewhere to type it
    return redirect('verify_email')


@login_required
def verify_email(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        ev = EmailVerification.objects.filter(
            user=request.user, is_verified=False, expires_at__gt=timezone.now()
        ).first()
        if not ev:
            messages.error(request, 'No active verification request. Please request a new code.')
            return redirect('profile')
        if ev.is_expired:
            messages.error(request, 'Verification code has expired. Please request a new one.')
            return redirect('profile')
        if ev.code != code:
            messages.error(request, 'Invalid verification code.')
            return render(request, 'verification/verify_email.html')
        ev.is_verified = True
        ev.verified_at = timezone.now()
        ev.save()
        if request.user.verification_level < 1:
            request.user.verification_level = 1
            request.user.save(update_fields=['verification_level'])
        UserNotification.notify(request.user, 'Email Verified', 'Your email has been verified successfully.', UserNotification.Type.VERIFICATION)
        messages.success(request, 'Email verified successfully!')
        return redirect('profile')
    return render(request, 'verification/verify_email.html')


@login_required
def send_phone_verification(request):
    """
    Placeholder — SMS sending is not yet wired up.

    When an SMS provider is connected (Termii, Twilio, etc.), replace
    this with a real implementation. For now, show a clear message so
    the user knows why nothing is happening.
    """
    messages.info(
        request,
        'Phone verification is coming soon. We will notify you when it is available.'
    )
    return redirect('profile')


@login_required
def verify_phone(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        pv = PhoneVerification.objects.filter(
            user=request.user, is_verified=False, expires_at__gt=timezone.now()
        ).first()
        if not pv:
            messages.error(request, 'No active phone verification. Please request a new code.')
            return redirect('profile')
        if pv.is_expired:
            messages.error(request, 'Code expired. Please request a new one.')
            return redirect('profile')
        if pv.code != code:
            messages.error(request, 'Invalid code.')
            return render(request, 'verification/verify_phone.html')
        pv.is_verified = True
        pv.verified_at = timezone.now()
        pv.save()
        request.user.phone_verified = True
        if request.user.verification_level < 2:
            request.user.verification_level = 2
        request.user.save(update_fields=['phone_verified', 'verification_level'])
        UserNotification.notify(request.user, 'Phone Verified', 'Your phone number has been verified.', UserNotification.Type.VERIFICATION)
        messages.success(request, 'Phone verified successfully!')
        return redirect('profile')
    return render(request, 'verification/verify_phone.html')


@login_required
def upload_vendor_document(request):
    if not hasattr(request.user, 'vendor_profile'):
        messages.error(request, 'You need a vendor profile to upload documents.')
        return redirect('dashboard')
    if request.method == 'POST':
        doc_type = request.POST.get('doc_type', 'other')
        name = request.POST.get('name', '').strip()
        file = request.FILES.get('file')
        if not name or not file:
            messages.error(request, 'Document name and file are required.')
            return render(request, 'verification/upload_document.html')
        VendorDocument.objects.create(
            vendor=request.user.vendor_profile,
            doc_type=doc_type,
            name=name,
            file=file,
        )
        UserNotification.notify(request.user, 'Document Submitted', f'Your document "{name}" has been submitted for review.', UserNotification.Type.VERIFICATION)
        messages.success(request, 'Document uploaded for review.')
        return redirect('vendor_dashboard')
    return render(request, 'verification/upload_document.html')


@login_required
def notification_center(request):
    notifications = request.user.notifications.all()[:50]
    unread_count = request.user.notifications.filter(is_read=False).count()
    return render(request, 'notifications/center.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
def mark_notification_read(request, notification_id):
    notif = get_object_or_404(UserNotification, id=notification_id, user=request.user)
    notif.mark_read()
    return redirect('notification_center')


@login_required
def mark_all_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True, read_at=timezone.now())
    messages.success(request, 'All notifications marked as read.')
    return redirect('notification_center')
