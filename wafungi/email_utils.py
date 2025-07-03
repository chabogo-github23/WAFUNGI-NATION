from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_email_with_template(subject, template_name, context, recipient_list, from_email=None):
    """
    Send email using HTML and text templates
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL
    
    try:
        # Render HTML template
        html_content = render_to_string(f'emails/{template_name}.html', context)
        
        # Try to render text template, fallback to stripped HTML
        try:
            text_content = render_to_string(f'emails/{template_name}.txt', context)
        except:
            text_content = strip_tags(html_content)
        
        # Create email message
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=recipient_list
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Send email
        result = msg.send()
        logger.info(f"Email sent successfully to {recipient_list}: {subject}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_list}: {str(e)}")
        return False

def send_booking_confirmation_email(booking):
    """
    Send booking confirmation email to client
    """
    subject = f"Booking Confirmation - {booking.id}"
    context = {
        'booking': booking,
        'client': booking.client,
        'musician': booking.musician,
        'instrument_listing': booking.instrument_listing,
    }
    
    return send_email_with_template(
        subject=subject,
        template_name='booking_confirmation',
        context=context,
        recipient_list=[booking.client.email]
    )

def send_payment_receipt_email(booking, payment_details):
    """
    Send payment receipt email
    """
    subject = f"Payment Receipt - Booking #{booking.id}"
    context = {
        'booking': booking,
        'payment_details': payment_details,
        'client': booking.client,
    }
    
    return send_email_with_template(
        subject=subject,
        template_name='payment_receipt',
        context=context,
        recipient_list=[booking.client.email]
    )

def send_booking_status_update_email(booking):
    """
    Send booking status update email
    """
    status_messages = {
        'confirmed': 'Your booking has been confirmed!',
        'cancelled': 'Your booking has been cancelled.',
        'completed': 'Your booking has been completed.',
    }
    
    subject = f"Booking Update - {status_messages.get(booking.status, 'Status Updated')}"
    context = {
        'booking': booking,
        'client': booking.client,
        'status_message': status_messages.get(booking.status, 'Your booking status has been updated.'),
    }
    
    return send_email_with_template(
        subject=subject,
        template_name='booking_status_update',
        context=context,
        recipient_list=[booking.client.email]
    )

def send_rental_request_email(booking):
    """
    Send rental request email to instrument owner
    """
    subject = f"New Rental Request - {booking.instrument_listing.instrument.name}"
    context = {
        'booking': booking,
        'owner': booking.instrument_listing.owner,
        'client': booking.client,
        'instrument': booking.instrument_listing,
    }
    
    return send_email_with_template(
        subject=subject,
        template_name='rental_request',
        context=context,
        recipient_list=[booking.instrument_listing.owner.email]
    )

def send_booking_accepted_email(booking):
    """
    Send booking accepted email to client
    """
    subject = f"Booking Accepted - {booking.instrument_listing.instrument.name}"
    context = {
        'booking': booking,
        'client': booking.client,
        'owner': booking.instrument_listing.owner,
        'instrument': booking.instrument_listing,
    }
    
    return send_email_with_template(
        subject=subject,
        template_name='booking_accepted',
        context=context,
        recipient_list=[booking.client.email]
    )

def send_booking_declined_email(booking):
    """
    Send booking declined email to client
    """
    subject = f"Booking Declined - {booking.instrument_listing.instrument.name}"
    context = {
        'booking': booking,
        'client': booking.client,
        'owner': booking.instrument_listing.owner,
        'instrument': booking.instrument_listing,
    }
    
    return send_email_with_template(
        subject=subject,
        template_name='booking_declined',
        context=context,
        recipient_list=[booking.client.email]
    )

def send_welcome_email(user):
    """
    Send welcome email to new users
    """
    subject = "Welcome to Wafungi Nation!"
    context = {
        'user': user,
        'user_type': user.get_user_type_display(),
    }
    
    return send_email_with_template(
        subject=subject,
        template_name='welcome',
        context=context,
        recipient_list=[user.email]
    )

def send_payment_confirmation_email(booking, transaction_id):
    """
    Send payment confirmation email
    """
    subject = f"Payment Confirmed - Booking #{booking.id}"
    context = {
        'booking': booking,
        'transaction_id': transaction_id,
        'client': booking.client,
        'amount': booking.total_amount,
    }
    
    return send_email_with_template(
        subject=subject,
        template_name='payment_confirmation',
        context=context,
        recipient_list=[booking.client.email]
    )

def send_musician_booking_notification(booking):
    """
    Send booking notification to musician
    """
    subject = f"New Booking Request - {booking.event.title if booking.event else 'Performance'}"
    context = {
        'booking': booking,
        'musician': booking.musician,
        'client': booking.client,
        'event': booking.event,
    }
    
    return send_email_with_template(
        subject=subject,
        template_name='musician_booking_notification',
        context=context,
        recipient_list=[booking.musician.email]
    )

def send_contact_form_email(form_data):
    """
    Send contact form submission email
    """
    subject = f"Contact Form: {form_data['subject']}"
    context = {
        'name': form_data['name'],
        'email': form_data['email'],
        'subject': form_data['subject'],
        'message': form_data['message'],
    }
    
    return send_email_with_template(
        subject=subject,
        template_name='contact_form',
        context=context,
        recipient_list=[settings.DEFAULT_FROM_EMAIL]
    )
