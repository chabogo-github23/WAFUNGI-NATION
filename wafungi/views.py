from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Sum
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging

from .models import (
    User, MusicianProfile, Event, Booking, InstrumentListing, 
    Genre, Instrument, Review, Notification, EventApplication, PaymentTransaction
)
from .forms import (
    UserRegistrationForm, ProfileSetupForm, MusicianProfileForm,
    EventForm, InstrumentListingForm, BookingForm, InstrumentRentalForm,
    EventApplicationForm
)
from .email_utils import (
    send_booking_confirmation_email, send_payment_receipt_email,
    send_booking_status_update_email, send_welcome_email
)
from .mpesa_utils import process_mpesa_payment, handle_mpesa_callback
from .pdf_utils import generate_payment_receipt_pdf

logger = logging.getLogger(__name__)

def home(request):
    """Home page view"""
    # Get featured musicians (top rated)
    featured_musicians = MusicianProfile.objects.filter(
        user__is_active=True,
        availability_status=True
    ).order_by('-rating', '-total_gigs')[:6]
    
    # Get upcoming events
    upcoming_events = Event.objects.filter(
        is_active=True,
        date__gte=timezone.now()
    ).order_by('date')[:6]
    
    # Get featured instruments
    featured_instruments = InstrumentListing.objects.filter(
        is_available=True
    ).order_by('-created_at')[:6]
    
    context = {
        'featured_musicians': featured_musicians,
        'upcoming_events': upcoming_events,
        'featured_instruments': featured_instruments,
    }
    return render(request, 'wafungi/home.html', context)

@login_required
def dashboard(request):
    """User dashboard view"""
    user = request.user
    context = {'user': user}
    
    # Get user-specific data based on user type
    if user.user_type == 'musician':
        try:
            profile = user.musicianprofile
            recent_bookings = Booking.objects.filter(
                musician=user
            ).order_by('-created_at')[:5]
            
            total_earnings = Booking.objects.filter(
                musician=user,
                payment_status=True
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            # Get event applications
            my_applications = EventApplication.objects.filter(
                musician=user
            ).order_by('-applied_at')[:5]
            
            context.update({
                'profile': profile,
                'recent_bookings': recent_bookings,
                'total_earnings': total_earnings,
                'my_applications': my_applications,
            })
        except MusicianProfile.DoesNotExist:
            messages.info(request, 'Please complete your musician profile.')
            return redirect('profile_setup')
    
    elif user.user_type == 'organizer':
        my_events = Event.objects.filter(organizer=user).order_by('-created_at')[:5]
        my_bookings = Booking.objects.filter(
            client=user
        ).order_by('-created_at')[:5]
        
        # Get pending applications for organizer's events
        pending_applications = EventApplication.objects.filter(
            event__organizer=user,
            status='pending'
        ).select_related('musician', 'event').order_by('-applied_at')[:5]
        
        context.update({
            'my_events': my_events,
            'my_bookings': my_bookings,
            'pending_applications': pending_applications,
        })
    
    elif user.user_type == 'instrument_owner':
        my_instruments = InstrumentListing.objects.filter(
            owner=user
        ).order_by('-created_at')[:5]
        
        # Get pending rental requests
        pending_requests = Booking.objects.filter(
            instrument_listing__owner=user,
            status='pending'
        ).order_by('-created_at')
        
        # Get all instrument bookings
        instrument_bookings = Booking.objects.filter(
            instrument_listing__owner=user
        ).order_by('-created_at')[:5]
        
        context.update({
            'my_instruments': my_instruments,
            'instrument_bookings': instrument_bookings,
            'pending_requests': pending_requests,
            'pending_count': pending_requests.count(),
        })
    
    elif user.user_type == 'client':
        my_bookings = Booking.objects.filter(
            client=user
        ).order_by('-created_at')[:5]
        
        context.update({
            'my_bookings': my_bookings,
        })
    
    # Get recent notifications
    context['notifications'] = Notification.objects.filter(
        user=user,
        is_read=False
    ).order_by('-created_at')[:5]
    
    return render(request, 'wafungi/dashboard.html', context)

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            # Send welcome email
            send_welcome_email(user)
            
            messages.success(request, 'Registration successful! Please complete your profile.')
            return redirect('profile_setup')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile_setup(request):
    """Profile setup view for new users"""
    if request.method == 'POST':
        if request.user.user_type == 'musician':
            try:
                profile = request.user.musicianprofile
            except MusicianProfile.DoesNotExist:
                profile = MusicianProfile.objects.create(user=request.user)
            
            form = MusicianProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Musician profile setup completed!')
                return redirect('dashboard')
        else:
            # For non-musicians, just update basic user info
            user = request.user
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.phone = request.POST.get('phone', user.phone)
            user.location = request.POST.get('location', user.location)
            user.bio = request.POST.get('bio', user.bio)
            user.save()
            
            messages.success(request, 'Profile setup completed!')
            return redirect('dashboard')
    else:
        if request.user.user_type == 'musician':
            try:
                profile = request.user.musicianprofile
            except MusicianProfile.DoesNotExist:
                profile = MusicianProfile.objects.create(user=request.user)
            form = MusicianProfileForm(instance=profile)
        else:
            form = None
    
    return render(request, 'wafungi/profile_setup.html', {'form': form})

@login_required
def profile_view(request):
    """View user profile"""
    return render(request, 'wafungi/profile.html', {'user': request.user})

@login_required
def profile_edit(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = ProfileSetupForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile_view')
    else:
        form = ProfileSetupForm(instance=request.user)
    
    return render(request, 'wafungi/profile_edit.html', {'form': form})

def search_musicians(request):
    """Search and filter musicians"""
    musicians = MusicianProfile.objects.filter(
        user__is_active=True,
        availability_status=True
    ).select_related('user').prefetch_related('genres', 'instruments')
    
    # Apply filters
    genre_filter = request.GET.get('genre')
    if genre_filter:
        musicians = musicians.filter(genres__id=genre_filter)
    
    instrument_filter = request.GET.get('instrument')
    if instrument_filter:
        musicians = musicians.filter(instruments__id=instrument_filter)
    
    location_filter = request.GET.get('location')
    if location_filter:
        musicians = musicians.filter(user__location__icontains=location_filter)
    
    search_query = request.GET.get('q')
    if search_query:
        musicians = musicians.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(stage_name__icontains=search_query) |
            Q(user__bio__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(musicians, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'genres': Genre.objects.all(),
        'instruments': Instrument.objects.all(),
        'current_filters': {
            'genre': genre_filter,
            'instrument': instrument_filter,
            'location': location_filter,
            'q': search_query,
        }
    }
    
    return render(request, 'wafungi/search_musicians.html', context)

def musician_detail(request, musician_id):
    """View musician profile details"""
    musician = get_object_or_404(MusicianProfile, id=musician_id)
    
    # Get reviews
    reviews = Review.objects.filter(
        reviewee=musician.user
    ).order_by('-created_at')[:10]
    
    # Get recent bookings (for portfolio)
    recent_bookings = Booking.objects.filter(
        musician=musician.user,
        status='completed'
    ).order_by('-created_at')[:5]
    
    context = {
        'musician': musician,
        'reviews': reviews,
        'recent_bookings': recent_bookings,
        'can_book': request.user.is_authenticated and request.user != musician.user,
    }
    
    return render(request, 'wafungi/musician_detail.html', context)

@login_required
def book_musician(request, musician_id):
    """Book a musician"""
    musician_profile = get_object_or_404(MusicianProfile, id=musician_id)
    musician = musician_profile.user
    
    if request.user == musician:
        messages.error(request, "You cannot book yourself.")
        return redirect('musician_detail', musician_id)
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.client = request.user
            booking.musician = musician
            
            # Calculate total amount
            duration_hours = (booking.end_date - booking.start_date).total_seconds() / 3600
            base_amount = Decimal(str(duration_hours)) * musician_profile.hourly_rate
            service_fee = base_amount * Decimal('0.05')  # 5% service fee
            booking.total_amount = base_amount + service_fee
            
            booking.save()
            
            # Send confirmation email
            send_booking_confirmation_email(booking)
            
            messages.success(request, 'Booking request sent successfully!')
            return redirect('booking_detail', booking.id)
    else:
        form = BookingForm()
    
    context = {
        'form': form,
        'musician': musician_profile,
    }
    
    return render(request, 'wafungi/book_musician.html', context)

def browse_events(request):
    """Browse available events"""
    events = Event.objects.filter(
        is_active=True,
        date__gte=timezone.now()
    ).order_by('date')
    
    # Apply filters
    event_type_filter = request.GET.get('event_type')
    if event_type_filter:
        events = events.filter(event_type=event_type_filter)
    
    location_filter = request.GET.get('location')
    if location_filter:
        events = events.filter(location__icontains=location_filter)
    
    search_query = request.GET.get('q')
    if search_query:
        events = events.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(events, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'event_types': Event.EVENT_TYPES,
        'current_filters': {
            'event_type': event_type_filter,
            'location': location_filter,
            'q': search_query,
        }
    }
    
    return render(request, 'wafungi/browse_events.html', context)

def event_detail(request, event_id):
    """View event details"""
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user can apply for this event
    can_apply = (
        request.user.is_authenticated and
        request.user.user_type == 'musician' and
        request.user != event.organizer and
        event.is_active and
        event.date > timezone.now()
    )
    
    # Check if user has already applied
    has_applied = False
    if request.user.is_authenticated and can_apply:
        has_applied = EventApplication.objects.filter(
            event=event,
            musician=request.user
        ).exists()
    
    context = {
        'event': event,
        'can_apply': can_apply and not has_applied,
        'has_applied': has_applied,
    }
    
    return render(request, 'wafungi/event_detail.html', context)

@login_required
def apply_for_event(request, event_id):
    """Apply for an event as a musician"""
    event = get_object_or_404(Event, id=event_id)
    
    # Check permissions
    if request.user.user_type != 'musician':
        messages.error(request, "Only musicians can apply for events.")
        return redirect('event_detail', event_id)
    
    if request.user == event.organizer:
        messages.error(request, "You cannot apply for your own event.")
        return redirect('event_detail', event_id)
    
    if not event.is_active or event.date <= timezone.now():
        messages.error(request, "This event is no longer accepting applications.")
        return redirect('event_detail', event_id)
    
    # Check if already applied
    if EventApplication.objects.filter(event=event, musician=request.user).exists():
        messages.info(request, "You have already applied for this event.")
        return redirect('event_detail', event_id)
    
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
                title='New Event Application',
                message=f'{request.user.get_full_name() or request.user.username} has applied to perform at your event "{event.title}".'
            )
            
            messages.success(request, 'Your application has been submitted successfully! The event organizer will review it.')
            return redirect('event_detail', event_id)
    else:
        form = EventApplicationForm(event=event)
    
    context = {
        'form': form,
        'event': event,
    }
    
    return render(request, 'wafungi/apply_for_event.html', context)

@login_required
def my_applications(request):
    """View musician's event applications"""
    if request.user.user_type != 'musician':
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    applications = EventApplication.objects.filter(
        musician=request.user
    ).select_related('event').order_by('-applied_at')
    
    # Pagination
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'wafungi/my_applications.html', {'page_obj': page_obj})

@login_required
def event_applications(request, event_id):
    """View applications for an event (organizer only)"""
    event = get_object_or_404(Event, id=event_id, organizer=request.user)
    
    applications = EventApplication.objects.filter(
        event=event
    ).select_related('musician').order_by('-applied_at')
    
    context = {
        'event': event,
        'applications': applications,
    }
    
    return render(request, 'wafungi/event_applications.html', context)

@login_required
@require_POST
def accept_application(request, application_id):
    """Accept an event application"""
    application = get_object_or_404(EventApplication, id=application_id)
    
    # Check permissions
    if application.event.organizer != request.user:
        messages.error(request, "You don't have permission to manage this application.")
        return redirect('dashboard')
    
    if application.status != 'pending':
        messages.error(request, "This application has already been processed.")
        return redirect('event_applications', application.event.id)
    
    # Get organizer notes
    organizer_notes = request.POST.get('organizer_notes', '')
    
    application.status = 'accepted'
    application.organizer_notes = organizer_notes
    application.save()
    
    # Create notification for musician
    Notification.objects.create(
        user=application.musician,
        title='Application Accepted!',
        message=f'Great news! Your application for "{application.event.title}" has been accepted. {organizer_notes}'
    )
    
    messages.success(request, 'Application accepted successfully!')
    return redirect('event_applications', application.event.id)

@login_required
@require_POST
def decline_application(request, application_id):
    """Decline an event application"""
    application = get_object_or_404(EventApplication, id=application_id)
    
    # Check permissions
    if application.event.organizer != request.user:
        messages.error(request, "You don't have permission to manage this application.")
        return redirect('dashboard')
    
    if application.status != 'pending':
        messages.error(request, "This application has already been processed.")
        return redirect('event_applications', application.event.id)
    
    # Get organizer notes
    organizer_notes = request.POST.get('organizer_notes', 'No specific reason provided.')
    
    application.status = 'declined'
    application.organizer_notes = organizer_notes
    application.save()
    
    # Create notification for musician
    Notification.objects.create(
        user=application.musician,
        title='Application Update',
        message=f'Your application for "{application.event.title}" was not selected this time. {organizer_notes}'
    )
    
    messages.success(request, 'Application declined.')
    return redirect('event_applications', application.event.id)

@login_required
def create_event(request):
    """Create a new event"""
    if request.user.user_type not in ['organizer', 'client']:
        messages.error(request, "Only event organizers can create events.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, 'Event created successfully!')
            return redirect('event_detail', event.id)
    else:
        form = EventForm()
    
    return render(request, 'wafungi/create_event.html', {'form': form})

@login_required
def join_event(request, event_id):
    """Join an event as a musician (legacy - now redirects to apply)"""
    return redirect('apply_for_event', event_id)

def search_instruments(request):
    """Search and filter instruments"""
    instruments = InstrumentListing.objects.filter(
        is_available=True
    ).select_related('owner', 'instrument')
    
    # Apply filters
    instrument_filter = request.GET.get('instrument')
    if instrument_filter:
        instruments = instruments.filter(instrument__id=instrument_filter)
    
    condition_filter = request.GET.get('condition')
    if condition_filter:
        instruments = instruments.filter(condition=condition_filter)
    
    location_filter = request.GET.get('location')
    if location_filter:
        instruments = instruments.filter(location__icontains=location_filter)
    
    max_price = request.GET.get('max_price')
    if max_price:
        try:
            instruments = instruments.filter(daily_rate__lte=Decimal(max_price))
        except (ValueError, TypeError):
            pass
    
    search_query = request.GET.get('q')
    if search_query:
        instruments = instruments.filter(
            Q(brand__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(instruments, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'instruments': Instrument.objects.all(),
        'conditions': InstrumentListing.CONDITION_CHOICES,
        'current_filters': {
            'instrument': instrument_filter,
            'condition': condition_filter,
            'location': location_filter,
            'max_price': max_price,
            'q': search_query,
        }
    }
    
    return render(request, 'wafungi/search_instruments.html', context)

def instrument_detail(request, instrument_id):
    """View instrument details"""
    instrument = get_object_or_404(InstrumentListing, id=instrument_id)
    
    # Get reviews for the instrument owner
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
def rent_instrument(request, instrument_id):
    """Rent an instrument"""
    instrument = get_object_or_404(InstrumentListing, id=instrument_id)
    
    if request.user == instrument.owner:
        messages.error(request, "You cannot rent your own instrument.")
        return redirect('instrument_detail', instrument_id)
    
    if not instrument.is_available:
        messages.error(request, "This instrument is not available for rent.")
        return redirect('instrument_detail', instrument_id)
    
    if request.method == 'POST':
        form = InstrumentRentalForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.client = request.user
            booking.instrument_listing = instrument
            
            # Calculate total amount
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # Convert dates to datetime for calculation
            if isinstance(start_date, datetime):
                start_date = timezone.make_aware(start_date) if timezone.is_naive(start_date) else start_date
            else:
                start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
                
            if isinstance(end_date, datetime):
                end_date = timezone.make_aware(end_date) if timezone.is_naive(end_date) else end_date
            else:
                end_date = timezone.make_aware(datetime.combine(end_date, datetime.min.time()))
            
            booking.start_date = start_date
            booking.end_date = end_date
            
            rental_days = (end_date - start_date).days
            if rental_days <= 0:
                rental_days = 1  # Minimum 1 day rental
            
            base_amount = instrument.daily_rate * rental_days
            service_fee = base_amount * Decimal('0.05')  # 5% service fee
            booking.total_amount = base_amount + service_fee
            
            booking.save()
            
            # Send confirmation email
            send_booking_confirmation_email(booking)
            
            # Create notification for instrument owner
            Notification.objects.create(
                user=instrument.owner,
                title='New Rental Request',
                message=f'{request.user.get_full_name() or request.user.username} has requested to rent your {instrument.brand} {instrument.model} for {rental_days} days.'
            )
            
            messages.success(request, 'Rental request sent successfully! The owner will review your request.')
            return redirect('booking_detail', booking.id)
    else:
        form = InstrumentRentalForm()
    
    return render(request, 'wafungi/rent_instrument.html', {
        'form': form,
        'instrument': instrument
    })

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
def my_bookings(request):
    """View user's bookings"""
    if request.user.user_type == 'client':
        bookings = Booking.objects.filter(client=request.user)
    elif request.user.user_type == 'musician':
        bookings = Booking.objects.filter(musician=request.user)
    elif request.user.user_type == 'instrument_owner':
        bookings = Booking.objects.filter(instrument_listing__owner=request.user)
    else:
        bookings = Booking.objects.none()
    
    bookings = bookings.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'wafungi/my_bookings.html', {'page_obj': page_obj})

@login_required
def booking_detail(request, booking_id):
    """View booking details"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check if user has permission to view this booking
    if not (booking.client == request.user or 
            booking.musician == request.user or 
            (booking.instrument_listing and booking.instrument_listing.owner == request.user)):
        messages.error(request, "You don't have permission to view this booking.")
        return redirect('dashboard')
    
    context = {
        'booking': booking,
        'can_confirm': (
            booking.status == 'pending' and
            (booking.musician == request.user or 
             (booking.instrument_listing and booking.instrument_listing.owner == request.user))
        ),
        'can_decline': (
            booking.status == 'pending' and
            (booking.musician == request.user or 
             (booking.instrument_listing and booking.instrument_listing.owner == request.user))
        ),
        'can_cancel': booking.status in ['pending', 'confirmed'] and booking.client == request.user,
        'can_pay': (
            booking.status == 'confirmed' and 
            not booking.payment_status and 
            booking.client == request.user
        ),
    }
    
    return render(request, 'wafungi/booking_detail.html', context)

@login_required
@require_POST
def accept_booking(request, booking_id):
    """Accept a booking request"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permissions
    if not (booking.musician == request.user or 
            (booking.instrument_listing and booking.instrument_listing.owner == request.user)):
        messages.error(request, "You don't have permission to accept this booking.")
        return redirect('booking_detail', booking_id)
    
    if booking.status != 'pending':
        messages.error(request, "This booking cannot be accepted.")
        return redirect('booking_detail', booking_id)
    
    old_status = booking.status
    booking.status = 'confirmed'
    booking.save()
    
    # Send status update email
    send_booking_status_update_email(booking)
    
    # Create notification for client
    if booking.instrument_listing:
        item_name = f"{booking.instrument_listing.brand} {booking.instrument_listing.model}"
    else:
        item_name = "musician booking"
    
    Notification.objects.create(
        user=booking.client,
        title='Booking Accepted!',
        message=f'Great news! Your {item_name} booking has been accepted. You can now proceed with payment.'
    )
    
    # Create notification for owner
    Notification.objects.create(
        user=request.user,
        title='Booking Accepted',
        message=f'You have accepted the booking request from {booking.client.get_full_name() or booking.client.username}.'
    )
    
    messages.success(request, 'Booking accepted successfully! The client has been notified and can now proceed with payment.')
    return redirect('booking_detail', booking_id)

@login_required
@require_POST
def decline_booking(request, booking_id):
    """Decline a booking request"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permissions
    if not (booking.musician == request.user or 
            (booking.instrument_listing and booking.instrument_listing.owner == request.user)):
        messages.error(request, "You don't have permission to decline this booking.")
        return redirect('booking_detail', booking_id)
    
    if booking.status != 'pending':
        messages.error(request, "This booking cannot be declined.")
        return redirect('booking_detail', booking_id)
    
    # Get decline reason from form
    decline_reason = request.POST.get('decline_reason', 'No reason provided')
    
    old_status = booking.status
    booking.status = 'cancelled'
    booking.notes = f"Declined by owner. Reason: {decline_reason}"
    booking.save()
    
    # Send status update email
    send_booking_status_update_email(booking)
    
    # Create notification for client
    if booking.instrument_listing:
        item_name = f"{booking.instrument_listing.brand} {booking.instrument_listing.model}"
    else:
        item_name = "musician booking"
    
    Notification.objects.create(
        user=booking.client,
        title='Booking Declined',
        message=f'Unfortunately, your {item_name} booking has been declined. Reason: {decline_reason}'
    )
    
    # Create notification for owner
    Notification.objects.create(
        user=request.user,
        title='Booking Declined',
        message=f'You have declined the booking request from {booking.client.get_full_name() or booking.client.username}.'
    )
    
    messages.success(request, 'Booking declined. The client has been notified.')
    return redirect('dashboard')

@login_required
def confirm_booking(request, booking_id):
    """Confirm a booking (legacy function - now using accept_booking)"""
    return accept_booking(request, booking_id)

@login_required
def cancel_booking(request, booking_id):
    """Cancel a booking"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permissions
    if booking.client != request.user:
        messages.error(request, "You don't have permission to cancel this booking.")
        return redirect('booking_detail', booking_id)
    
    if booking.status not in ['pending', 'confirmed']:
        messages.error(request, "This booking cannot be cancelled.")
        return redirect('booking_detail', booking_id)
    
    if booking.payment_status:
        messages.error(request, "Cannot cancel a paid booking. Please contact support.")
        return redirect('booking_detail', booking_id)
    
    old_status = booking.status
    booking.status = 'cancelled'
    booking.save()
    
    # Send status update email
    send_booking_status_update_email(booking)
    
    # Create notification for service provider
    if booking.instrument_listing:
        Notification.objects.create(
            user=booking.instrument_listing.owner,
            title='Booking Cancelled',
            message=f'{booking.client.get_full_name() or booking.client.username} has cancelled their rental request for {booking.instrument_listing.brand} {booking.instrument_listing.model}.'
        )
    
    messages.success(request, 'Booking cancelled successfully!')
    return redirect('dashboard')

@login_required
def payment_process(request, booking_id):
    """Process payment for booking"""
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)
    
    if booking.payment_status:
        messages.info(request, 'This booking has already been paid for.')
        return redirect('booking_detail', booking.id)
    
    if booking.status != 'confirmed':
        messages.error(request, 'This booking must be confirmed before payment.')
        return redirect('booking_detail', booking.id)
    
    if request.method == 'POST':
        mpesa_number = request.POST.get('mpesa_number')
        
        if not mpesa_number:
            messages.error(request, 'Please provide your M-Pesa phone number.')
            return render(request, 'wafungi/payment.html', {'booking': booking})
        
        # Validate phone number format
        mpesa_number = ''.join(filter(str.isdigit, mpesa_number))
        if len(mpesa_number) != 9:
            messages.error(request, 'Please enter a valid 9-digit phone number (e.g., 712345678).')
            return render(request, 'wafungi/payment.html', {'booking': booking})
        
        # Process M-Pesa payment
        try:
            # Get recipient phone number
            recipient_phone = booking.get_recipient_phone()
            
            payment_result = process_mpesa_payment(
                phone_number=mpesa_number,
                amount=float(booking.total_amount),
                booking_id=booking.id,
                recipient_phone=recipient_phone
            )
            
            if payment_result['success']:
                # Create payment transaction record
                transaction = PaymentTransaction.objects.create(
                    booking=booking,
                    checkout_request_id=payment_result['checkout_request_id'],
                    merchant_request_id=payment_result.get('merchant_request_id', ''),
                    phone_number=f"254{mpesa_number}",
                    amount=booking.total_amount,
                    status='pending',
                    mpesa_response=payment_result
                )
                
                messages.success(request, 
                    f"Payment request sent successfully! Please check your phone for the M-Pesa prompt and enter your PIN to complete the payment. "
                    f"Transaction ID: {payment_result['checkout_request_id']}")
                
                # Redirect to payment status page
                return redirect('payment_status', booking.id, transaction.checkout_request_id)
            else:
                error_message = payment_result.get('error', 'Payment failed')
                messages.error(request, f'Payment failed: {error_message}')
                logger.error(f"Payment failed for booking {booking.id}: {payment_result}")
                
        except Exception as e:
            messages.error(request, f'Payment processing error: {str(e)}')
            logger.error(f"Payment processing error for booking {booking.id}: {str(e)}")
    
    return render(request, 'wafungi/payment.html', {'booking': booking})

@login_required
def payment_status(request, booking_id, checkout_request_id):
    """Check payment status and handle completion"""
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)
    transaction = get_object_or_404(PaymentTransaction, 
                                  booking=booking, 
                                  checkout_request_id=checkout_request_id)
    
    # Check if payment is already completed
    if transaction.status == 'completed':
        return redirect('payment_success', booking.id)
    
    # For demo purposes, we'll simulate payment completion after 30 seconds
    # In production, this would be handled by M-Pesa callbacks
    if request.method == 'POST' and request.POST.get('simulate_payment'):
        # Simulate successful payment
        transaction.status = 'completed'
        transaction.transaction_id = f'MPESA{booking.id}{timezone.now().strftime("%Y%m%d%H%M%S")}'
        transaction.save()
        
        # Update booking payment status
        booking.payment_status = True
        booking.save()
        
        # Send payment receipt email
        send_payment_receipt_email(booking, {
            'transaction_id': transaction.transaction_id,
            'payment_date': timezone.now(),
            'amount': booking.total_amount,
            'phone_number': transaction.phone_number
        })
        
        # Create notifications
        service_provider = booking.get_service_provider()
        if service_provider:
            if booking.instrument_listing:
                item_name = f"{booking.instrument_listing.brand} {booking.instrument_listing.model}"
            else:
                item_name = "musician booking"
            
            Notification.objects.create(
                user=service_provider,
                title='Payment Received',
                message=f'Payment of KSH {booking.total_amount:,.0f} has been received for the {item_name} booking.'
            )
        
        Notification.objects.create(
            user=booking.client,
            title='Payment Successful',
            message=f'Your payment of KSH {booking.total_amount:,.0f} was successful. Receipt sent to your email.'
        )
        
        return redirect('payment_success', booking.id)
    
    context = {
        'booking': booking,
        'transaction': transaction,
        'checkout_request_id': checkout_request_id,
    }
    
    return render(request, 'wafungi/payment_status.html', context)

@login_required
def payment_success(request, booking_id):
    """Payment success page with receipt download"""
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)
    
    if not booking.payment_status:
        messages.error(request, "Payment not completed yet.")
        return redirect('booking_detail', booking_id)
    
    # Get the latest completed transaction
    transaction = PaymentTransaction.objects.filter(
        booking=booking,
        status='completed'
    ).first()
    
    context = {
        'booking': booking,
        'transaction': transaction,
    }
    
    return render(request, 'wafungi/payment_success.html', context)

@login_required
def download_receipt(request, booking_id):
    """Download payment receipt as PDF"""
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)
    
    if not booking.payment_status:
        messages.error(request, "No payment found for this booking.")
        return redirect('booking_detail', booking_id)
    
    # Get the transaction details
    transaction = PaymentTransaction.objects.filter(
        booking=booking,
        status='completed'
    ).first()
    
    transaction_id = transaction.transaction_id if transaction else f'RECEIPT-{booking.id}'
    
    # Generate and return PDF
    return generate_payment_receipt_pdf(booking, transaction_id)

@login_required
def payment_cancel(request, booking_id):
    """Payment cancelled page"""
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)
    return render(request, 'wafungi/payment_cancel.html', {'booking': booking})

@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa payment callbacks"""
    if request.method == 'POST':
        try:
            callback_data = json.loads(request.body.decode('utf-8'))
            logger.info(f"M-Pesa callback received: {callback_data}")
            
            # Process the callback
            result = handle_mpesa_callback(callback_data)
            
            if result['success']:
                # Find the transaction
                checkout_request_id = result['checkout_request_id']
                try:
                    transaction = PaymentTransaction.objects.get(
                        checkout_request_id=checkout_request_id
                    )
                    
                    # Update transaction
                    transaction.status = 'completed'
                    transaction.transaction_id = result['transaction_id']
                    transaction.save()
                    
                    # Update booking
                    booking = transaction.booking
                    booking.payment_status = True
                    booking.save()
                    
                    # Send notifications and emails
                    send_payment_receipt_email(booking, result)
                    
                    logger.info(f"Payment completed for booking {booking.id}")
                    
                except PaymentTransaction.DoesNotExist:
                    logger.error(f"Transaction not found for checkout_request_id: {checkout_request_id}")
            else:
                # Handle failed payment
                checkout_request_id = result.get('checkout_request_id')
                if checkout_request_id:
                    try:
                        transaction = PaymentTransaction.objects.get(
                            checkout_request_id=checkout_request_id
                        )
                        transaction.status = 'failed'
                        transaction.save()
                        logger.info(f"Payment failed for transaction {checkout_request_id}")
                    except PaymentTransaction.DoesNotExist:
                        pass
            
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
            
        except Exception as e:
            logger.error(f"Error processing M-Pesa callback: {str(e)}")
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Error'})
    
    return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid request'})

# Email Preview Views (for development/testing)
@login_required
def preview_payment_receipt(request, booking_id):
    """Preview payment receipt email (HTML version)"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    booking = get_object_or_404(Booking, id=booking_id)
    transaction_id = f"MPESA{booking.id}{timezone.now().strftime('%Y%m%d%H%M%S')}"
    
    context = {
        'booking': booking,
        'transaction_id': transaction_id,
        'payment_date': timezone.now(),
        'client': booking.client,
        'site_name': 'WAFUNGI-NATION',
        'booking_type': 'Instrument Rental' if booking.instrument_listing else 'Musician Booking',
        'item': booking.instrument_listing or booking.musician,
        'owner': booking.get_service_provider(),
    }
    
    return render(request, 'emails/payment_receipt.html', context)

@login_required
def preview_payment_receipt_text(request, booking_id):
    """Preview payment receipt email (text version)"""
    if not request.user.is_staff:
        return HttpResponse("Access denied.", status=403)
    
    booking = get_object_or_404(Booking, id=booking_id)
    transaction_id = f"MPESA{booking.id}{timezone.now().strftime('%Y%m%d%H%M%S')}"
    
    context = {
        'booking': booking,
        'transaction_id': transaction_id,
        'payment_date': timezone.now(),
        'client': booking.client,
        'site_name': 'WAFUNGI-NATION',
        'booking_type': 'Instrument Rental' if booking.instrument_listing else 'Musician Booking',
        'item': booking.instrument_listing or booking.musician,
        'owner': booking.get_service_provider(),
    }
    
    content = render_to_string('emails/payment_receipt.txt', context)
    return HttpResponse(content, content_type='text/plain')

@login_required
def preview_booking_confirmation(request, booking_id):
    """Preview booking confirmation email (HTML version)"""
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    booking = get_object_or_404(Booking, id=booking_id)
    
    context = {
        'booking': booking,
    }
    
    return render(request, 'emails/booking_confirmation.html', context)

@login_required
def preview_booking_confirmation_text(request, booking_id):
    """Preview booking confirmation email (text version)"""
    if not request.user.is_staff:
        return HttpResponse("Access denied.", status=403)
    
    booking = get_object_or_404(Booking, id=booking_id)
    
    context = {
        'booking': booking,
    }
    
    content = render_to_string('emails/booking_confirmation.txt', context)
    return HttpResponse(content, content_type='text/plain')
