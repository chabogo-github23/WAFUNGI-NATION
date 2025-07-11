from reportlab.lib.pagesizes import letter, A4 # type: ignore
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle # type: ignore
from reportlab.lib.units import inch # type: ignore
from reportlab.lib import colors # type: ignore
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image # type: ignore
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT # type: ignore
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from io import BytesIO
from decimal import Decimal
import os

def generate_payment_receipt_pdf(booking, transaction_id, payment_date=None):
    """
    Generate a PDF receipt for a payment
    
    Args:
        booking: Booking instance
        transaction_id: M-Pesa transaction ID
        payment_date: Payment date (defaults to now)
    
    Returns:
        HttpResponse with PDF content
    """
    if payment_date is None:
        payment_date = timezone.now()
    
    # Create a BytesIO buffer to receive PDF data
    buffer = BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2c3e50')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#34495e')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6
    )
    
    # Add title
    title = Paragraph("WAFUNGI-NATION", title_style)
    elements.append(title)
    
    subtitle = Paragraph("Payment Receipt", heading_style)
    elements.append(subtitle)
    elements.append(Spacer(1, 20))
    
    # Receipt information
    receipt_info = [
        ['Receipt Number:', f"#{booking.id}-{payment_date.strftime('%Y%m%d')}"],
        ['Transaction ID:', transaction_id],
        ['Payment Date:', payment_date.strftime('%B %d, %Y at %I:%M %p')],
        ['Status:', 'PAID'],
    ]
    
    receipt_table = Table(receipt_info, colWidths=[2*inch, 3*inch])
    receipt_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(receipt_table)
    elements.append(Spacer(1, 20))
    
    # Customer information
    customer_heading = Paragraph("Customer Information", heading_style)
    elements.append(customer_heading)
    
    customer_info = [
        ['Name:', booking.client.get_full_name() or booking.client.username],
        ['Email:', booking.client.email],
        ['Phone:', booking.client.phone or 'Not provided'],
    ]
    
    customer_table = Table(customer_info, colWidths=[2*inch, 3*inch])
    customer_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(customer_table)
    elements.append(Spacer(1, 20))
    
    # Service details
    service_heading = Paragraph("Service Details", heading_style)
    elements.append(service_heading)
    
    # Determine service type and details
    if booking.instrument_listing:
        service_type = "Instrument Rental"
        service_name = f"{booking.instrument_listing.brand} {booking.instrument_listing.model}"
        provider = booking.instrument_listing.owner.get_full_name() or booking.instrument_listing.owner.username
        daily_rate = booking.instrument_listing.daily_rate
        
        # Calculate rental days
        rental_days = (booking.end_date.date() - booking.start_date.date()).days
        if rental_days <= 0:
            rental_days = 1
            
        service_details = [
            ['Service Type:', service_type],
            ['Instrument:', service_name],
            ['Provider:', provider],
            ['Rental Period:', f"{booking.start_date.strftime('%b %d, %Y')} to {booking.end_date.strftime('%b %d, %Y')}"],
            ['Duration:', f"{rental_days} day{'s' if rental_days != 1 else ''}"],
            ['Daily Rate:', f"KSH {daily_rate:,.2f}"],
        ]
    else:
        service_type = "Musician Booking"
        service_name = "Musical Performance"
        provider = booking.musician.get_full_name() or booking.musician.username
        
        # Calculate duration in hours
        duration_hours = (booking.end_date - booking.start_date).total_seconds() / 3600
        
        service_details = [
            ['Service Type:', service_type],
            ['Service:', service_name],
            ['Musician:', provider],
            ['Event Date:', booking.start_date.strftime('%B %d, %Y')],
            ['Duration:', f"{duration_hours:.1f} hours"],
        ]
    
    service_table = Table(service_details, colWidths=[2*inch, 3*inch])
    service_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(service_table)
    elements.append(Spacer(1, 20))
    
    # Payment breakdown
    payment_heading = Paragraph("Payment Breakdown", heading_style)
    elements.append(payment_heading)
    
    # Calculate amounts
    service_fee = booking.total_amount * Decimal('0.05')  # 5% service fee
    subtotal = booking.total_amount - service_fee
    
    payment_data = [
        ['Subtotal:', f"KSH {subtotal:,.2f}"],
        ['Service Fee (5%):', f"KSH {service_fee:,.2f}"],
        ['', ''],  # Empty row for spacing
        ['Total Amount Paid:', f"KSH {booking.total_amount:,.2f}"],
    ]
    
    payment_table = Table(payment_data, colWidths=[3*inch, 2*inch])
    payment_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -2), 'Helvetica'),
        ('FONTNAME', (1, 0), (1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -2), 11),
        ('FONTSIZE', (0, -1), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#27ae60')),
    ]))
    
    elements.append(payment_table)
    elements.append(Spacer(1, 30))
    
    # Footer notes
    notes_heading = Paragraph("Important Notes", heading_style)
    elements.append(notes_heading)
    
    notes = [
        "• This is an official receipt for your payment",
        "• Please keep this receipt for your records",
        "• Contact the service provider for pickup/delivery arrangements",
        "• For any issues, contact our support team at support@wafungi-nation.com",
    ]
    
    if booking.instrument_listing:
        notes.extend([
            "• Return the instrument in the same condition to avoid additional charges",
            "• Late returns may incur additional fees"
        ])
    
    for note in notes:
        note_para = Paragraph(note, normal_style)
        elements.append(note_para)
    
    elements.append(Spacer(1, 30))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    
    footer_text = f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}<br/>WAFUNGI-NATION - Connecting Musicians, Organizers & Instrument Owners"
    footer = Paragraph(footer_text, footer_style)
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and return it as HttpResponse
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt-{booking.id}-{payment_date.strftime("%Y%m%d")}.pdf"'
    response.write(pdf)
    
    return response

def generate_booking_summary_pdf(booking):
    """
    Generate a PDF summary for a booking
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Add content similar to receipt but for booking summary
    title = Paragraph("WAFUNGI-NATION - Booking Summary", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Add booking details...
    # (Implementation similar to receipt but focused on booking info)
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="booking-summary-{booking.id}.pdf"'
    response.write(pdf)
    
    return response
