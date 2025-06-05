from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import *
from .forms import *

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

def instrument_detail(request, instrument_id):
    """Instrument listing detail"""
    instrument = get_object_or_404(InstrumentListing, id=instrument_id)
    
    context = {
        'instrument': instrument,
    }
    
    return render(request, 'wafungi/instrument_detail.html', context)

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
    booking = get_object_or_404(
        Booking, 
        id=booking_id
    )
    
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
