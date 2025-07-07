from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q
from .models import Event, InstrumentListing, EventApplication, Notification, MusicianProfile
from .forms import InstrumentListingForm, EventApplicationForm

def event_detail(request, event_id):
    """View event details"""
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user can apply for this event
    can_apply = False
    has_applied = False
    user_application = None
    
    if request.user.is_authenticated and request.user.user_type == 'musician':
        can_apply = (
            request.user != event.organizer and
            event.is_active and
            event.date > timezone.now()
        )
        
        # Check if user has already applied
        try:
            user_application = EventApplication.objects.get(event=event, musician=request.user)
            has_applied = True
        except EventApplication.DoesNotExist:
            pass
    
    # Get total applications count for the organizer
    total_applications = event.applications.count() if request.user == event.organizer else None
    
    context = {
        'event': event,
        'can_apply': can_apply,
        'has_applied': has_applied,
        'user_application': user_application,
        'total_applications': total_applications,
    }
    
    return render(request, 'wafungi/event_detail.html', context)

@login_required
def apply_for_event(request, event_id):
    """Apply for an event as a musician"""
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is a musician
    if request.user.user_type != 'musician':
        messages.error(request, "Only musicians can apply for events.")
        return redirect('event_detail', event_id)
    
    # Check if user is the event organizer
    if request.user == event.organizer:
        messages.error(request, "You cannot apply for your own event.")
        return redirect('event_detail', event_id)
    
    # Check if event is still active and in the future
    if not event.is_active or event.date <= timezone.now():
        messages.error(request, "This event is no longer accepting applications.")
        return redirect('event_detail', event_id)
    
    # Check if user has already applied
    if EventApplication.objects.filter(event=event, musician=request.user).exists():
        messages.info(request, "You have already applied for this event.")
        return redirect('event_detail', event_id)
    
    # Check if musician has a complete profile
    try:
        musician_profile = request.user.musicianprofile
    except MusicianProfile.DoesNotExist:
        messages.error(request, "Please complete your musician profile before applying for events.")
        return redirect('profile_setup')
    
    if request.method == 'POST':
        form = EventApplicationForm(request.POST, event=event)
        if form.is_valid():
            application = form.save(commit=False)
            application.event = event
            application.musician = request.user
            application.save()
            
            # Create notification for event organizer
            Notification.objects.create(
                user=event.organizer,
                title=f'New Event Application - {event.title}',
                message=f'{request.user.get_full_name() or request.user.username} has applied to perform at your event "{event.title}". Proposed rate: KSH {application.proposed_rate:,.0f}'
            )
            
            # Create confirmation notification for musician
            Notification.objects.create(
                user=request.user,
                title=f'Application Submitted - {event.title}',
                message=f'Your application for "{event.title}" has been submitted successfully. The organizer will review your application and get back to you.'
            )
            
            messages.success(request, 'Your application has been submitted successfully! The event organizer will review it and get back to you.')
            return redirect('event_detail', event_id)
    else:
        # Pre-fill proposed rate with musician's hourly rate if available
        initial_data = {}
        if hasattr(request.user, 'musicianprofile') and request.user.musicianprofile.hourly_rate:
            # Suggest rate based on event duration and musician's hourly rate
            suggested_rate = request.user.musicianprofile.hourly_rate * event.duration_hours
            initial_data['proposed_rate'] = suggested_rate
        
        form = EventApplicationForm(event=event, initial=initial_data)
    
    context = {
        'form': form,
        'event': event,
        'musician_profile': musician_profile,
    }
    
    return render(request, 'wafungi/apply_for_event.html', context)

@login_required
def view_event_applications(request, event_id):
    """View applications for an event (organizer only)"""
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user is the event organizer
    if request.user != event.organizer:
        messages.error(request, "You don't have permission to view applications for this event.")
        return redirect('event_detail', event_id)
    
    applications = event.applications.select_related('musician', 'musician__musicianprofile').order_by('-applied_at')
    
    context = {
        'event': event,
        'applications': applications,
    }
    
    return render(request, 'wafungi/event_applications.html', context)

@login_required
@require_POST
def respond_to_application(request, application_id):
    """Accept or decline an event application"""
    application = get_object_or_404(EventApplication, id=application_id)
    
    # Check if user is the event organizer
    if request.user != application.event.organizer:
        messages.error(request, "You don't have permission to respond to this application.")
        return redirect('dashboard')
    
    action = request.POST.get('action')
    organizer_notes = request.POST.get('organizer_notes', '')
    
    if action == 'accept':
        application.status = 'accepted'
        application.organizer_notes = organizer_notes
        application.save()
        
        # Create notification for musician
        Notification.objects.create(
            user=application.musician,
            title=f'Application Accepted - {application.event.title}',
            message=f'Great news! Your application for "{application.event.title}" has been accepted. The organizer will contact you soon with further details.'
        )
        
        messages.success(request, f'Application from {application.musician.get_full_name() or application.musician.username} has been accepted.')
        
    elif action == 'decline':
        application.status = 'declined'
        application.organizer_notes = organizer_notes
        application.save()
        
        # Create notification for musician
        Notification.objects.create(
            user=application.musician,
            title=f'Application Update - {application.event.title}',
            message=f'Thank you for your interest in "{application.event.title}". Unfortunately, we have decided to go with other musicians for this event. We encourage you to apply for future events.'
        )
        
        messages.success(request, f'Application from {application.musician.get_full_name() or application.musician.username} has been declined.')
    
    else:
        messages.error(request, 'Invalid action.')
    
    return redirect('view_event_applications', application.event.id)

def instrument_detail(request, instrument_id):
    """View instrument details"""
    instrument = get_object_or_404(InstrumentListing, id=instrument_id)
    
    # Get reviews for the instrument owner
    from .models import Review
    owner_reviews = Review.objects.filter(
        reviewee=instrument.owner
    ).order_by('-created_at')[:5]
    
    context = {
        'instrument': instrument,
        'owner_reviews': owner_reviews,
        'can_rent': request.user.is_authenticated and request.user != instrument.owner,
    }
    
    return render(request, 'wafungi/instrument_detail.html', context)

@login_required
def add_instrument(request):
    """Add a new instrument listing"""
    if request.user.user_type not in ['instrument_owner', 'musician']:
        messages.error(request, "Only instrument owners can add instruments.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = InstrumentListingForm(request.POST, request.FILES)
        if form.is_valid():
            instrument_listing = form.save(commit=False)
            instrument_listing.owner = request.user
            instrument_listing.save()
            
            messages.success(request, 'Instrument added successfully!')
            return redirect('instrument_detail', instrument_listing.id)
    else:
        form = InstrumentListingForm()
    
    return render(request, 'wafungi/add_instrument.html', {'form': form})

@login_required
def my_applications(request):
    """View musician's event applications"""
    if request.user.user_type != 'musician':
        messages.error(request, "Only musicians can view applications.")
        return redirect('dashboard')
    
    applications = EventApplication.objects.filter(
        musician=request.user
    ).select_related('event', 'event__organizer').order_by('-applied_at')
    
    context = {
        'applications': applications,
    }
    
    return render(request, 'wafungi/my_applications.html', context)

@login_required
@require_POST
def withdraw_application(request, application_id):
    """Withdraw an event application"""
    application = get_object_or_404(EventApplication, id=application_id, musician=request.user)
    
    if application.status != 'pending':
        messages.error(request, "You can only withdraw pending applications.")
        return redirect('my_applications')
    
    application.status = 'withdrawn'
    application.save()
    
    # Create notification for organizer
    Notification.objects.create(
        user=application.event.organizer,
        title=f'Application Withdrawn - {application.event.title}',
        message=f'{request.user.get_full_name() or request.user.username} has withdrawn their application for "{application.event.title}".'
    )
    
    messages.success(request, 'Your application has been withdrawn.')
    return redirect('my_applications')
