from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Sum
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from decimal import Decimal
from .models import (
    User, MusicianProfile, Event, Booking, InstrumentListing, 
    Genre, Instrument, Review, Notification
)
from .forms import (
    UserRegistrationForm, ProfileSetupForm, MusicianProfileForm,
    EventForm, InstrumentListingForm, BookingForm, InstrumentRentalForm
)
from .email_utils import (
    send_booking_confirmation_email, send_payment_receipt_email,
    send_booking_status_update_email, send_welcome_email
)
from .mpesa_utils import process_mpesa_payment
import logging

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
            
            context.update({
                'profile': profile,
                'recent_bookings': recent_bookings,
                'total_earnings': total_earnings,
            })
        except MusicianProfile.DoesNotExist:
            messages.info(request, 'Please complete your musician profile.')
            return redirect('profile_setup')
    
    elif user.user_type == 'organizer':
        my_events = Event.objects.filter(organizer=user).order_by('-created_at')[:5]
        my_bookings = Booking.objects.filter(
            client=user
        ).order_by('-created_at')[:5]
        
        context.update({
            'my_events': my_events,
            'my_bookings': my_bookings,
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
    
    # Check if user can join this event
    can_join = (
        request.user.is_authenticated and
        request.user.user_type == 'musician' and
        request.user != event.organizer and
        event.is_active and
        event.date > timezone.now()
    )
    
    context = {
        'event': event,
        'can_join': can_join,
    }
    
    return render(request, 'wafungi/event_detail.html', context)

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
    """Join an event as a musician"""
    event = get_object_or_404(Event, id=event_id)
    
    if request.user.user_type != 'musician':
        messages.error(request, "Only musicians can join events.")
        return redirect('event_detail', event_id)
    
    if request.user == event.organizer:
        messages.error(request, "You cannot join your own event.")
        return redirect('event_detail', event_id)
    
    # Create a booking for the event
    booking, created = Booking.objects.get_or_create(
        client=request.user,
        event=event,
        defaults={
            'start_date': event.date,
            'end_date': event.date + timedelta(hours=event.duration_hours),
            'total_amount': (event.budget_min + event.budget_max) / 2,
            'status': 'pending',
        }
    )
    
    if created:
        messages.success(request, 'Successfully applied to join the event!')
    else:
        messages.info(request, 'You have already applied for this event.')
    
    return redirect('event_detail', event_id)

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
    def send_booking_status_update_email(booking):
        subject = f"Booking status changed to {booking.status}"
    #send_booking_status_update_email(booking, old_status, 'confirmed')
    
    # Create notification for client
    Notification.objects.create(
        user=booking.client,
        title='Booking Accepted!',
        message=f'Great news! Your rental request for {booking.instrument_listing.brand} {booking.instrument_listing.model} has been accepted. You can now proceed with payment.'
    )
    
    # Create notification for owner
    Notification.objects.create(
        user=request.user,
        title='Booking Accepted',
        message=f'You have accepted the rental request from {booking.client.get_full_name() or booking.client.username}.'
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
    send_booking_status_update_email(booking, old_status, 'cancelled')
    
    # Create notification for client
    Notification.objects.create(
        user=booking.client,
        title='Booking Declined',
        message=f'Unfortunately, your rental request for {booking.instrument_listing.brand} {booking.instrument_listing.model} has been declined. Reason: {decline_reason}'
    )
    
    # Create notification for owner
    Notification.objects.create(
        user=request.user,
        title='Booking Declined',
        message=f'You have declined the rental request from {booking.client.get_full_name() or booking.client.username}.'
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
    send_booking_status_update_email(booking, old_status, 'cancelled')
    
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
        if not mpesa_number.isdigit() or len(mpesa_number) != 9:
            messages.error(request, 'Please enter a valid 9-digit phone number (e.g., 712345678).')
            return render(request, 'wafungi/payment.html', {'booking': booking})
        
        # Process M-Pesa payment
        try:
            # For demo purposes, simulate successful payment
            # In production, use actual M-Pesa API
            payment_result = {
                'success': True,
                'transaction_id': f'MPESA{booking.id}{timezone.now().strftime("%Y%m%d%H%M%S")}'
            }
            
            if payment_result['success']:
                booking.payment_status = True
                booking.save()
                
                # Send payment receipt
                transaction_id = payment_result.get('transaction_id')
                send_payment_receipt_email(booking, transaction_id)
                
                # Create notifications
                if booking.instrument_listing:
                    recipient = booking.instrument_listing.owner
                    item_name = f"{booking.instrument_listing.brand} {booking.instrument_listing.model}"
                else:
                    recipient = booking.musician
                    item_name = "musician booking"
                
                Notification.objects.create(
                    user=recipient,
                    title='Payment Received',
                    message=f'Payment of KSH {booking.total_amount:,.0f} has been received for the {item_name} booking.'
                )
                
                Notification.objects.create(
                    user=booking.client,
                    title='Payment Successful',
                    message=f'Your payment of KSH {booking.total_amount:,.0f} was successful. Receipt sent to your email.'
                )
                
                messages.success(request, 'Payment processed successfully via M-Pesa! Receipt has been sent to your email.')
                return redirect('booking_detail', booking.id)
            else:
                messages.error(request, 'Payment failed. Please try again.')
                
        except Exception as e:
            messages.error(request, f'Payment processing error: {str(e)}')
    
    return render(request, 'wafungi/payment.html', {'booking': booking})

@login_required
def payment_success(request, booking_id):
    """Payment success page"""
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)
    return render(request, 'wafungi/payment_success.html', {'booking': booking})

@login_required
def payment_cancel(request, booking_id):
    """Payment cancelled page"""
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)
    return render(request, 'wafungi/payment_cancel.html', {'booking': booking})

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
