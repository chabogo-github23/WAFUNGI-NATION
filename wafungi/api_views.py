from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Notification
import json
from django.utils import timezone

@login_required
def get_notifications(request):
    """API endpoint to get user notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
    unread_count = notifications.filter(is_read=False).count()
    
    notification_data = []
    for notification in notifications:
        notification_data.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'is_read': notification.is_read,
            'created_at': notification.created_at.strftime('%b %d, %Y %H:%M'),
        })
    
    return JsonResponse({
        'notifications': notification_data,
        'unread_count': unread_count
    })

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """API endpoint to mark a notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

@login_required
def get_musician_availability(request, musician_id):
    """API endpoint to get musician availability"""
    from .models import MusicianProfile, Booking
    from datetime import datetime, timedelta
    
    try:
        musician = MusicianProfile.objects.get(id=musician_id)
        
        # Get bookings for the next 30 days
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)
        
        bookings = Booking.objects.filter(
            musician=musician.user,
            start_date__gte=start_date,
            end_date__lte=end_date,
            status__in=['confirmed', 'pending']
        ).values('start_date', 'end_date')
        
        # Format bookings for calendar
        booking_data = []
        for booking in bookings:
            booking_data.append({
                'start': booking['start_date'].isoformat(),
                'end': booking['end_date'].isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'availability_status': musician.availability_status,
            'bookings': booking_data
        })
    except MusicianProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Musician not found'}, status=404)

@login_required
def get_instrument_availability(request, instrument_id):
    """API endpoint to get instrument availability"""
    from .models import InstrumentListing, Booking
    from datetime import datetime, timedelta
    
    try:
        instrument = InstrumentListing.objects.get(id=instrument_id)
        
        # Get bookings for the next 30 days
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)
        
        bookings = Booking.objects.filter(
            instrument_listing=instrument,
            start_date__gte=start_date,
            end_date__lte=end_date,
            status__in=['confirmed', 'pending']
        ).values('start_date', 'end_date')
        
        # Format bookings for calendar
        booking_data = []
        for booking in bookings:
            booking_data.append({
                'start': booking['start_date'].isoformat(),
                'end': booking['end_date'].isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'is_available': instrument.is_available,
            'bookings': booking_data
        })
    except InstrumentListing.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Instrument not found'}, status=404)

@login_required
def search_api(request):
    """API endpoint for search suggestions"""
    query = request.GET.get('q', '')
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    from .models import MusicianProfile, InstrumentListing, Event, Genre, Instrument
    from django.db.models import Q
    
    # Search musicians
    musicians = MusicianProfile.objects.filter(
        Q(stage_name__icontains=query) |
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query)
    )[:5]
    
    # Search instruments
    instruments = InstrumentListing.objects.filter(
        Q(brand__icontains=query) |
        Q(model__icontains=query) |
        Q(instrument__name__icontains=query)
    )[:5]
    
    # Search events
    events = Event.objects.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query)
    )[:5]
    
    # Search genres
    genres = Genre.objects.filter(name__icontains=query)[:5]
    
    # Search instrument types
    instrument_types = Instrument.objects.filter(name__icontains=query)[:5]
    
    results = []
    
    # Format results
    for musician in musicians:
        results.append({
            'type': 'musician',
            'id': musician.id,
            'name': musician.stage_name or f"{musician.user.first_name} {musician.user.last_name}",
            'url': f"/musicians/{musician.id}/",
            'image': musician.user.profile_picture.url if musician.user.profile_picture else None,
        })
    
    for instrument in instruments:
        results.append({
            'type': 'instrument',
            'id': instrument.id,
            'name': f"{instrument.brand} {instrument.model}",
            'url': f"/instruments/{instrument.id}/",
            'image': instrument.image.url if instrument.image else None,
        })
    
    for event in events:
        results.append({
            'type': 'event',
            'id': event.id,
            'name': event.title,
            'url': f"/events/{event.id}/",
        })
    
    for genre in genres:
        results.append({
            'type': 'genre',
            'id': genre.id,
            'name': genre.name,
            'url': f"/musicians/?genre={genre.id}",
        })
    
    for instrument_type in instrument_types:
        results.append({
            'type': 'instrument_type',
            'id': instrument_type.id,
            'name': instrument_type.name,
            'url': f"/instruments/?instrument={instrument_type.id}",
        })
    
    return JsonResponse({'results': results})
