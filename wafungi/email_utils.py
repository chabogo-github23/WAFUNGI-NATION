from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def send_payment_receipt_email(booking, transaction_id=None):
    """
    Send payment receipt email to the client
    """
    try:
        # Prepare email context
        context = {
            'booking': booking,
            'client': booking.client,
            'transaction_id': transaction_id,
            'payment_date': timezone.now(),
            'site_name': 'WAFUNGI-NATION',
        }
        
        # Determine the type of booking for email content
        if booking.instrument_listing:
            context['booking_type'] = 'Instrument Rental'
            context['item'] = f"{booking.instrument_listing.brand} {booking.instrument_listing.model}"
            context['owner'] = booking.instrument_listing.owner
        elif booking.musician:
            context['booking_type'] = 'Musician Booking'
            context['item'] = booking.musician.get_full_name() or booking.musician.username
            context['owner'] = booking.musician
        else:
            context['booking_type'] = 'Service Booking'
            context['item'] = 'Service'
            context['owner'] = None
        
        # Render email templates
        subject = f'Payment Receipt - Booking #{booking.id} - WAFUNGI-NATION'
        html_content = render_to_string('emails/payment_receipt.html', context)
        text_content = render_to_string('emails/payment_receipt.txt', context)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[booking.client.email],
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send()
        
        logger.info(f"Payment receipt email sent successfully for booking #{booking.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send payment receipt email for booking #{booking.id}: {str(e)}")
        return False

def send_booking_confirmation_email(booking):
    """
    Send booking confirmation email to both client and service provider
    """
    try:
        # Email to client
        client_context = {
            'booking': booking,
            'recipient': booking.client,
            'is_client': True,
            'site_name': 'WAFUNGI-NATION',
        }
        
        if booking.instrument_listing:
            client_context['booking_type'] = 'Instrument Rental'
            client_context['item'] = f"{booking.instrument_listing.brand} {booking.instrument_listing.model}"
            client_context['provider'] = booking.instrument_listing.owner
        elif booking.musician:
            client_context['booking_type'] = 'Musician Booking'
            client_context['item'] = booking.musician.get_full_name() or booking.musician.username
            client_context['provider'] = booking.musician
        
        # Send to client
        subject_client = f'Booking Confirmation - #{booking.id} - WAFUNGI-NATION'
        html_content_client = render_to_string('emails/booking_confirmation.html', client_context)
        text_content_client = render_to_string('emails/booking_confirmation.txt', client_context)
        
        email_client = EmailMultiAlternatives(
            subject=subject_client,
            body=text_content_client,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[booking.client.email],
        )
        email_client.attach_alternative(html_content_client, "text/html")
        email_client.send()
        
        # Email to service provider
        if booking.instrument_listing:
            provider = booking.instrument_listing.owner
        elif booking.musician:
            provider = booking.musician
        else:
            provider = None
        
        if provider and provider.email:
            provider_context = {
                'booking': booking,
                'recipient': provider,
                'is_client': False,
                'client': booking.client,
                'site_name': 'WAFUNGI-NATION',
            }
            
            if booking.instrument_listing:
                provider_context['booking_type'] = 'Instrument Rental'
                provider_context['item'] = f"{booking.instrument_listing.brand} {booking.instrument_listing.model}"
            elif booking.musician:
                provider_context['booking_type'] = 'Musician Booking'
                provider_context['item'] = booking.musician.get_full_name() or booking.musician.username
            
            subject_provider = f'New Booking Request - #{booking.id} - WAFUNGI-NATION'
            html_content_provider = render_to_string('emails/booking_confirmation.html', provider_context)
            text_content_provider = render_to_string('emails/booking_confirmation.txt', provider_context)
            
            email_provider = EmailMultiAlternatives(
                subject=subject_provider,
                body=text_content_provider,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[provider.email],
            )
            email_provider.attach_alternative(html_content_provider, "text/html")
            email_provider.send()
        
        logger.info(f"Booking confirmation emails sent successfully for booking #{booking.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send booking confirmation emails for booking #{booking.id}: {str(e)}")
        return False
