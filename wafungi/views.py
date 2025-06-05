from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import *
from .forms import *
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
                ).aggregate(total=models.Sum('total_amount'))['total'] or 0,
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
        musicians = musicians.filter(hourly_rate__gte=min_rate)
    
    if max_rate:
        musicians = musicians.filter(hourly_rate__lte=max_rate)
    
    # Pagination
    paginator = Paginator(musicians, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'genres': Genre.objects.all(),
        'instruments': Instrument.objects.all(),
        'current_filters': {
            'q': query,
            'genre': genre,
            'instrument': instrument,
            'location': location,
            'min_rate': min_rate,
            'max_rate': max_rate,
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
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.client = request.user
            booking.musician = musician.user
            
            # Calculate total amount
            duration = booking.end_date - booking.start_date
            hours = duration.total_seconds() / 3600
            booking.total_amount = musician.hourly_rate * hours
            
            booking.save()
            
            # Create notification
            Notification.objects.create(
                user=musician.user,
                title='New Booking Request',
                message=f'{request.user.get_full_name()} has requested to book you.'
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
            Q(description__icontains=query)
        )
    
    if instrument_type:
        instruments = instruments.filter(instrument__id=instrument_type)
    
    if location:
        instruments = instruments.filter(location__icontains=location)
    
    if condition:
        instruments = instruments.filter(condition=condition)
    
    if max_rate:
        instruments = instruments.filter(daily_rate__lte=max_rate)
    
    # Pagination
    paginator = Paginator(instruments, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'instrument_types': Instrument.objects.all(),
        'conditions': InstrumentListing.CONDITION_CHOICES,
        'current_filters': {
            'q': query,
            'instrument': instrument_type,
            'location': location,
            'condition': condition,
            'max_rate': max_rate,
        }
    }
    
    return render(request, 'wafungi/search_instruments.html', context)

@login_required
def create_event(request):
    """Create a new event"""
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

@login_required
@require_POST
def confirm_booking(request, booking_id):
    """Confirm a booking (for musicians)"""
    booking = get_object_or_404(Booking, id=booking_id, musician=request.user)
    
    if booking.status == 'pending':
        booking.status = 'confirmed'
        booking.save()
        
        # Create notification for client
        Notification.objects.create(
            user=booking.client,
            title='Booking Confirmed',
            message=f'Your booking with {request.user.get_full_name()} has been confirmed.'
        )
        
        messages.success(request, 'Booking confirmed successfully!')
    
    return redirect('dashboard')

@login_required
def payment_process(request, booking_id):
    """Process payment for booking"""
    booking = get_object_or_404(Booking, id=booking_id, client=request.user)
    
    if request.method == 'POST':
        
        booking.payment_status = True
        booking.save()
        
        # Create notification
        Notification.objects.create(
            user=booking.musician,
            title='Payment Received',
            message=f'Payment of ${booking.total_amount} has been received for your booking.'
        )
        
        messages.success(request, 'Payment processed successfully!')
        return redirect('dashboard')
    
    return render(request, 'wafungi/payment.html', {'booking': booking})
