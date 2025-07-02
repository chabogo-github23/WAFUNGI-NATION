from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from .models import *
from .forms import *
from .email_utils import send_payment_receipt_email, send_booking_confirmation_email
import json

def home(request):
    """Homepage with search functionality"""
    featured_musicians = MusicianProfile.objects.filter(
        availability_status=True
    ).order_by('-rating')[:6]

    recent_events = Event.objects.filter(
        is_active=True
    ).order_by('-created_at')[:4]

    available_instruments = InstrumentListing.objects.filter(
        is_available=True
    ).order_by('-created_at')[:6]

    context = {
        'featured_musicians': featured_musicians,
        'recent_events': recent_events,
        'available_instruments': available_instruments,
        'genres': Genre.objects.all(),
        'instruments': Instrument.objects.all(),
    }
    return render(request, 'wafungi/home.html', context)

def register(request):
    """User registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            
            # Create profile based on user type
            if user.user_type == 'musician':
                MusicianProfile.objects.create(user=user)
            
            login(request, user)
            return redirect('profile_setup')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile_setup(request):
    """Profile setup after registration"""
    if request.user.user_type == 'musician':
        try:
            profile = request.user.musicianprofile
        except MusicianProfile.DoesNotExist:
            profile = MusicianProfile.objects.create(user=request.user)
        
        if request.method == 'POST':
            form = MusicianProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('dashboard')
        else:
            form = MusicianProfileForm(instance=profile)
        
        return render(request, 'wafungi/profile_setup.html', {'form': form})

    return redirect('dashboard')

@login_required
def dashboard(request):
    """User dashboard"""
    context = {}

    if request.user.user_type == 'musician':
        try:
            profile = request.user.musicianprofile
            context.update({
                'profile': profile,
                'recent_bookings': Booking.objects.filter(
                    musician=request.user
                ).order_by('-created_at')[:5],
                'total_earnings': Booking.objects.filter(
                    musician=request.user,
                    status='completed',
                    payment_status=True
                ).aggregate(total=Sum('total_amount'))['total'] or 0,
            })
        except MusicianProfile.DoesNotExist:
            return redirect('profile_setup')

    elif request.user.user_type == 'organizer':
        context.update({
            'my_events': Event.objects.filter(
                organizer=request.user
            ).order_by('-created_at')[:5],
            'my_bookings': Booking.objects.filter(
                client=request.user
            ).order_by('-created_at')[:5],
        })

    elif request.user.user_type == 'instrument_owner':
        context.update({
            'my_instruments': InstrumentListing.objects.filter(
                owner=request.user
            ).order_by('-created_at')[:5],
            'instrument_bookings': Booking.objects.filter(
                instrument_listing__owner=request.user
            ).order_by('-created_at')[:5],
        })

    # Common context for all users
    context.update({
        'notifications': Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')[:5],
    })

    return render(request, 'wafungi/dashboard.html', context)

def search_musicians(request):
    """Search and filter musicians"""
    musicians = MusicianProfile.objects.filter(availability_status=True)

    # Search filters
    query = request.GET.get('q')
    genre = request.GET.get('genre')
    instrument = request.GET.get('instrument')
    location = request.GET.get('location')
    min_rate = request.GET.get('min_rate')
    max_rate = request.GET.get('max_rate')

    if query:
        musicians = musicians.filter(
            Q(stage_name__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__bio__icontains=query)
        )

    if genre:
        musicians = musicians.filter(genres__id=genre)

    if instrument:
        musicians = musicians.filter(instruments__id=instrument)

    if location:
        musicians = musicians.filter(user__location__icontains=location)

    if min_rate:
        try:
            musicians = musicians.filter(hourly_rate__gte=float(min_rate))
        except (ValueError, TypeError):
            pass

    if max_rate:
        try:
            musicians = musicians.filter(hourly_rate__lte=float(max_rate))
        except (ValueError, TypeError):
            pass

    # Remove duplicates and order
    musicians = musicians.distinct().order_by('-rating', '-user__date_joined')

    # Pagination
    paginator = Paginator(musicians, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'genres': Genre.objects.all(),
        'instruments': Instrument.objects.all(),
        'current_filters': {
            'q': query or '',
            'genre': genre or '',
            'instrument': instrument or '',
            'location': location or '',
            'min_rate': min_rate or '',
            'max_rate': max_rate or '',
        }
    }

    return render(request, 'wafungi/search_musicians.html', context)

def musician_detail(request, musician_id):
    """Musician profile detail"""
    musician = get_object_or_404(MusicianProfile, id=musician_id)
    reviews = Review.objects.filter(reviewee=musician.user).order_by('-created_at')

    context = {
        'musician': musician,
        'reviews': reviews,
        'can_book': request.user.is_authenticated and request.user != musician.user,
    }

    return render(request, 'wafungi/musician_detail.html', context)

@login_required
def book_musician(request, musician_id):
    """Book a musician"""
    musician = get_object_or_404(MusicianProfile, id=musician_id)

    if request.user == musician.user:
        messages.error(request, 'You cannot book yourself.')
        return redirect('musician_detail', musician_id)

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.client = request.user
            booking.musician = musician.user
            
            # Calculate total amount
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # Validate dates
            if end_date <= start_date:
                messages.error(request, 'End date must be after start date.')
                return render(request, 'wafungi/book_musician.html', {
                    'form': form,
                    'musician': musician
                })
            
            duration = end_date - start_date
            hours = duration.total_seconds() / 3600
            subtotal = float(musician.hourly_rate) * hours
            service_fee = subtotal * 0.05  # 5% service fee
            booking.total_amount = subtotal + service_fee
            
            booking.save()
            
            # Send booking confirmation email
            send_booking_confirmation_email(booking)
            
            # Create notification
            Notification.objects.create(
                user=musician.user,
                title='New Booking Request',
                message=f'{request.user.get_full_name() or request.user.username} has requested to book you for {hours:.1f} hours.'
            )
            
            messages.success(request, 'Booking request sent successfully!')
            return redirect('booking_detail', booking.id)
    else:
        form = BookingForm()

    return render(request, 'wafungi/book_musician.html', {
        'form': form,
        'musician': musician
    })

def search_instruments(request):
    """Search and filter instruments"""
    instruments = InstrumentListing.objects.filter(is_available=True)

    # Search filters
    query = request.GET.get('q')
    instrument_type = request.GET.get('instrument')
    location = request.GET.get('location')
    condition = request.GET.get('condition')
    max_rate = request.GET.get('max_rate')

    if query:
        instruments = instruments.filter(
            Q(brand__icontains=query) |
            Q(model__icontains=query) |
            Q(description__icontains=query) |
            Q(instrument__name__icontains=query)
        )

    if instrument_type:
        instruments = instruments.filter(instrument__id=instrument_type)

    if location:
        instruments = instruments.filter(location__icontains=location)

    if condition:
        instruments = instruments.filter(condition=condition)

    if max_rate:
        try:
            instruments = instruments.filter(daily_rate__lte=float(max_rate))
        except (ValueError, TypeError):
            pass

    # Order by creation date
    instruments = instruments.order_by('-created_at')

    # Pagination
    paginator = Paginator(instruments, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'instrument_types': Instrument.objects.all(),
        'conditions': InstrumentListing.CONDITION_CHOICES,
        'current_filters': {
            'q': query or '',
            'instrument': instrument_type or '',
            'location': location or '',
            'condition': condition or '',
            'max_rate': max_rate or '',
        }
    }

    return render(request, 'wafungi/search_instruments.html', context)

def instrument_detail(request, instrument_id):
    """Instrument listing detail"""
    instrument = get_object_or_404(InstrumentListing, id=instrument_id)

    context = {
        'instrument': instrument,
    }

    return render(request, 'wafungi/instrument_detail.html', context)

@login_required
def add_instrument(request):
    """Add a new instrument listing"""
    if request.user.user_type != 'instrument_owner':
        messages.error(request, 'Only instrument owners can list instruments.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = InstrumentListingForm(request.POST, request.FILES)
        if form.is_valid():
            instrument = form.save(commit=False)
            instrument.owner = request.user
            instrument.save()
            
            messages.success(request, 'Instrument listed successfully!')
            return redirect('instrument_detail', instrument.id)
    else:
        form = InstrumentListingForm()

    return render(request, 'wafungi/add_instrument.html', {'form': form})

@login_required
def rent_instrument(request, instrument_id):
    """Rent an instrument"""
    instrument = get_object_or_404(InstrumentListing, id=instrument_id)

    if not instrument.is_available:
        messages.error(request, 'This instrument is not available for rent.')
        return redirect('instrument_detail', instrument.id)

    if instrument.owner == request.user:
        messages.error(request, 'You cannot rent your own instrument.')
        return redirect('instrument_detail', instrument.id)

    if request.method == 'POST':
        form = InstrumentRentalForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.client = request.user
            booking.instrument_listing = instrument
            
            # Calculate total amount (without security deposit)
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']

            # Convert dates to datetime for calculation
            from datetime import date, datetime
            if isinstance(start_date, date) and not isinstance(start_date, datetime):
                start_date = datetime.combine(start_date, datetime.min.time())
            if isinstance(end_date, date) and not isinstance(end_date, datetime):
                end_date = datetime.combine(end_date, datetime.min.time())

            # Make dates timezone aware
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)

            booking.start_date = start_date
            booking.end_date = end_date

            rental_days = (end_date - start_date).days
            if rental_days <= 0:
                rental_days = 1  # Minimum 1 day rental

            subtotal = float(instrument.daily_rate) * rental_days
            service_fee = subtotal * 0.05  # 5% service fee
            booking.total_amount = subtotal + service_fee
            
            booking.save()
            
            # Send booking confirmation email
            send_booking_confirmation_email(booking)
            
            # Create notification for instrument owner
            Notification.objects.create(
                user=instrument.owner,
                title='New Rental Request',
                message=f'{request.user.get_full_name() or request.user.username} has requested to rent your {instrument.brand} {instrument.model} for {rental_days} days.'
            )
            
            # Create notification for client
            Notification.objects.create(
                user=request.user,
                title='Rental Request Sent',
                message=f'Your rental request for {instrument.brand} {instrument.model} has been sent to the owner.'
            )
            
            messages.success(request, 'Rental request sent successfully! The owner will contact you soon.')
            return redirect('booking_detail', booking.id)
    else:
        form = InstrumentRentalForm()

    return render(request, 'wafungi/rent_instrument.html', {
        'form': form,
        'instrument': instrument
    })

@login_required
def create_event(request):
    """Create a new event"""
    if request.user.user_type != 'organizer':
        messages.error(request, 'Only event organizers can create events.')
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

def browse_events(request):
    """Browse available events"""
    events = Event.objects.filter(is_active=True).order_by('-created_at')

    # Pagination
    paginator = Paginator(events, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'wafungi/browse_events.html', {'page_obj': page_obj})

def event_detail(request, event_id):
    """Event detail"""
    event = get_object_or_404(Event, id=event_id)

    context = {
        'event': event,
    }

    return render(request, 'wafungi/event_detail.html', context)

@login_required
def booking_detail(request, booking_id):
    """Booking detail"""
    # Ensure the user is authorized to view this booking
    booking = get_object_or_404(Booking, id=booking_id)

    # Check if user has permission to view this booking
    if not (booking.client == request.user or 
            booking.musician == request.user or 
            (booking.instrument_listing and booking.instrument_listing.owner == request.user)):
        messages.error(request, 'You do not have permission to view this booking.')
        return redirect('dashboard')

    context = {
        'booking': booking,
    }

    return render(request, 'wafungi/booking_detail.html', context)

@login_required
@require_POST
def confirm_booking(request, booking_id):
    """Confirm a booking (for musicians and instrument owners)"""
    booking = get_object_or_404(Booking, id=booking_id)

    # Check if user can confirm this booking
    can_confirm = (
        (booking.musician and booking.musician == request.user) or
        (booking.instrument_listing and booking.instrument_listing.owner == request.user)
    )

    if not can_confirm:
        messages.error(request, 'You do not have permission to confirm this booking.')
        return redirect('dashboard')

    if booking.status == 'pending':
        booking.status = 'confirmed'
        booking.save()
        
        # Create notification for client
        Notification.objects.create(
            user=booking.client,
            title='Booking Confirmed',
            message=f'Your booking #{booking.id} has been confirmed. Please proceed with payment.'
        )
        
        messages.success(request, 'Booking confirmed successfully!')
    else:
        messages.warning(request, 'This booking has already been processed.')

    return redirect('booking_detail', booking.id)

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
        
        # Format phone number for M-Pesa
        formatted_number = '254' + mpesa_number
        
        # Process M-Pesa payment
        try:
            # For now, we'll simulate successful payment
            # In production, you would use the actual M-Pesa API
            payment_result = {
                'success': True,
                'transaction_id': f'MPESA{booking.id}{timezone.now().strftime("%Y%m%d%H%M%S")}'
            }
            
            if payment_result['success']:
                booking.payment_status = True
                booking.save()
                
                # Send payment receipt email
                transaction_id = payment_result.get('transaction_id')
                email_sent = send_payment_receipt_email(booking, transaction_id)
                
                # Create notifications
                recipient = booking.musician or booking.instrument_listing.owner
                Notification.objects.create(
                    user=recipient,
                    title='Payment Received',
                    message=f'Payment of KSH {booking.total_amount:,.0f} has been received for booking #{booking.id}.'
                )
                
                Notification.objects.create(
                    user=booking.client,
                    title='Payment Successful',
                    message=f'Your payment of KSH {booking.total_amount:,.0f} for booking #{booking.id} was successful. Receipt sent to your email.'
                )
                
                if email_sent:
                    messages.success(request, 'Payment processed successfully via M-Pesa! Receipt has been sent to your email.')
                else:
                    messages.success(request, 'Payment processed successfully via M-Pesa! (Note: Receipt email could not be sent)')
                
                return redirect('booking_detail', booking.id)
            else:
                messages.error(request, 'Payment failed. Please try again.')
                
        except Exception as e:
            messages.error(request, f'Payment processing error: {str(e)}')

    return render(request, 'wafungi/payment.html', {'booking': booking})

# Email Template Preview Views (for development/testing)
@login_required
def preview_payment_receipt(request, booking_id):
    """Preview payment receipt email template (HTML)"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permission
    if booking.client != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this.')
        return redirect('dashboard')
    
    context = {
        'booking': booking,
        'transaction_id': 'SAMPLE123456789',
        'payment_date': timezone.now(),
    }
    
    return render(request, 'emails/payment_receipt.html', context)

@login_required
def preview_payment_receipt_text(request, booking_id):
    """Preview payment receipt email template (Text)"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permission
    if booking.client != request.user and not request.user.is_staff:
        return HttpResponse('Permission denied', status=403)
    
    context = {
        'booking': booking,
        'transaction_id': 'SAMPLE123456789',
        'payment_date': timezone.now(),
    }
    
    content = render_to_string('emails/payment_receipt.txt', context)
    return HttpResponse(content, content_type='text/plain')

@login_required
def preview_booking_confirmation(request, booking_id):
    """Preview booking confirmation email template (HTML)"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permission
    if booking.client != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this.')
        return redirect('dashboard')
    
    context = {
        'booking': booking,
    }
    
    return render(request, 'emails/booking_confirmation.html', context)

@login_required
def preview_booking_confirmation_text(request, booking_id):
    """Preview booking confirmation email template (Text)"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check permission
    if booking.client != request.user and not request.user.is_staff:
        return HttpResponse('Permission denied', status=403)
    
    context = {
        'booking': booking,
    }
    
    content = render_to_string('emails/booking_confirmation.txt', context)
    return HttpResponse(content, content_type='text/plain')
