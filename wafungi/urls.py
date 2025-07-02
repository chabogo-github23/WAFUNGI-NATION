from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from . import api_views
from . import additional_views 

urlpatterns = [
    # Home and authentication
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile-setup/', views.profile_setup, name='profile_setup'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Musicians
    path('musicians/', views.search_musicians, name='search_musicians'),
    path('musicians/<int:musician_id>/', views.musician_detail, name='musician_detail'),
    path('musicians/<int:musician_id>/book/', views.book_musician, name='book_musician'),
    
    # Events - Update these to use additional_views
    path('events/', views.browse_events, name='browse_events'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:event_id>/', additional_views.event_detail, name='event_detail'),  # Changed this line
    
    # Instruments - Update these to use additional_views
    path('instruments/', views.search_instruments, name='search_instruments'),
    path('instruments/<int:instrument_id>/', additional_views.instrument_detail, name='instrument_detail'),  # Changed this line
    path('instruments/add/', additional_views.add_instrument, name='add_instrument'),  # Changed this line
    path('instruments/<int:instrument_id>/rent/', views.rent_instrument, name='rent_instrument'),

    # Bookings - Update these to use additional_views
    path('bookings/<int:booking_id>/', additional_views.booking_detail, name='booking_detail'),  # Changed this line
    path('bookings/<int:booking_id>/confirm/', views.confirm_booking, name='confirm_booking'),
    path('bookings/<int:booking_id>/payment/', views.payment_process, name='payment_process'),
    
    # API endpoints
    path('api/notifications/', api_views.get_notifications, name='api_notifications'),
    path('api/mark-notification-read/<int:notification_id>/', api_views.mark_notification_read, name='mark_notification_read'),
    path('api/musician/<int:musician_id>/availability/', api_views.get_musician_availability, name='musician_availability'),
    path('api/instrument/<int:instrument_id>/availability/', api_views.get_instrument_availability, name='instrument_availability'),
    path('api/search/', api_views.search_api, name='search_api'),
    path('api/send-message/', api_views.send_message_to_owner, name='send_message_to_owner'),
    
    # Password reset
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # Email Template Previews
    path('email-preview/payment-receipt/<int:booking_id>/', views.preview_payment_receipt, name='preview_payment_receipt'),
    path('email-preview/booking-confirmation/<int:booking_id>/', views.preview_booking_confirmation, name='preview_booking_confirmation'),
    path('email-preview/payment-receipt-text/<int:booking_id>/', views.preview_payment_receipt_text, name='preview_payment_receipt_text'),
    path('email-preview/booking-confirmation-text/<int:booking_id>/', views.preview_booking_confirmation_text, name='preview_booking_confirmation_text'),
]


