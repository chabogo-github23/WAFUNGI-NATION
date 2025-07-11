from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views, api_views 

urlpatterns = [
    # Home and dashboard
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Authentication and profile
    path('register/', views.register, name='register'),
    path('profile-setup/', views.profile_setup, name='profile_setup'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    
    # Musicians
    path('musicians/', views.search_musicians, name='search_musicians'),
    path('musicians/<int:musician_id>/', views.musician_detail, name='musician_detail'),
    path('musicians/<int:musician_id>/book/', views.book_musician, name='book_musician'),
    
    # Dashboard
    #path('dashboard/', views.dashboard, name='dashboard'),
    
    # Events
    path('events/', views.browse_events, name='browse_events'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:event_id>/join/', views.join_event, name='join_event'),
    
    # Event Applications
    path('events/<int:event_id>/apply/', views.apply_for_event, name='apply_for_event'),
    path('events/<int:event_id>/applications/', views.event_applications, name='event_applications'),
    path('applications/', views.my_applications, name='my_applications'),
    path('applications/<int:application_id>/accept/', views.accept_application, name='accept_application'),
    path('applications/<int:application_id>/decline/', views.decline_application, name='decline_application'),
    
    # Instruments
    path('instruments/', views.search_instruments, name='search_instruments'),
    path('instruments/<int:instrument_id>/', views.instrument_detail, name='instrument_detail'),
    path('instruments/<int:instrument_id>/rent/', views.rent_instrument, name='rent_instrument'),
    path('instruments/add/', views.add_instrument, name='add_instrument'),
    
    # Bookings
    path('bookings/', views.my_bookings, name='my_bookings'),
    path('bookings/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/<int:booking_id>/accept/', views.accept_booking, name='accept_booking'),
    path('bookings/<int:booking_id>/decline/', views.decline_booking, name='decline_booking'),
    path('bookings/<int:booking_id>/confirm/', views.confirm_booking, name='confirm_booking'),
    path('bookings/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    
    # Payments
    path('bookings/<int:booking_id>/payment/', views.payment_process, name='payment_process'),
    path('bookings/<int:booking_id>/payment/status/<str:checkout_request_id>/', views.payment_status, name='payment_status'),
    path('bookings/<int:booking_id>/payment/success/', views.payment_success, name='payment_success'),
    path('bookings/<int:booking_id>/payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('bookings/<int:booking_id>/receipt/download/', views.download_receipt, name='download_receipt'),
    
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
    path('preview/payment-receipt/<int:booking_id>/', views.preview_payment_receipt, name='preview_payment_receipt'),
    path('preview/payment-receipt/<int:booking_id>/text/', views.preview_payment_receipt_text, name='preview_payment_receipt_text'),
    path('preview/booking-confirmation/<int:booking_id>/', views.preview_booking_confirmation, name='preview_booking_confirmation'),
    path('preview/booking-confirmation/<int:booking_id>/text/', views.preview_booking_confirmation_text, name='preview_booking_confirmation_text'),

    # M-Pesa Integration
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    #path('mpesa/confirmation/', mpesa_views.mpesa_confirmation, name='mpesa_confirmation'),
    #path('mpesa/validation/', mpesa_views.mpesa_validation, name='mpesa_validation'),
    
]
