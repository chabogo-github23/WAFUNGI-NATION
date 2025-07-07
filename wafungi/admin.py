from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import *

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'user_type', 'is_verified', 'date_joined')
    list_filter = ('user_type', 'is_verified', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone', 'location', 'bio', 'profile_picture', 'is_verified')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'email', 'first_name', 'last_name')
        }),
    )

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name', 'category')

@admin.register(MusicianProfile)
class MusicianProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'stage_name', 'experience_years', 'hourly_rate', 'availability_status', 'rating')
    list_filter = ('availability_status', 'experience_years', 'genres', 'instruments')
    search_fields = ('user__username'  'experience_years', 'genres', 'instruments')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'stage_name')
    filter_horizontal = ('genres', 'instruments')
    
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'Full Name'

@admin.register(InstrumentListing)
class InstrumentListingAdmin(admin.ModelAdmin):
    list_display = ('instrument', 'brand', 'model', 'owner', 'daily_rate', 'condition', 'is_available', 'location')
    list_filter = ('instrument', 'condition', 'is_available', 'created_at')
    search_fields = ('brand', 'model', 'owner__username', 'location')
    date_hierarchy = 'created_at'
    
    def get_owner_name(self, obj):
        return obj.owner.get_full_name() or obj.owner.username
    get_owner_name.short_description = 'Owner'

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'event_type', 'date', 'location', 'budget_range', 'is_active')
    list_filter = ('event_type', 'is_active', 'date', 'required_genres')
    search_fields = ('title', 'description', 'organizer__username', 'location')
    date_hierarchy = 'date'
    filter_horizontal = ('required_genres', 'required_instruments')
    
    def budget_range(self, obj):
        return f"${obj.budget_min} - ${obj.budget_max}"
    budget_range.short_description = 'Budget Range'

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'musician_or_instrument', 'start_date', 'total_amount', 'status', 'payment_status')
    list_filter = ('status', 'payment_status', 'start_date', 'created_at')
    search_fields = ('client__username', 'musician__username', 'notes')
    date_hierarchy = 'start_date'
    
    def musician_or_instrument(self, obj):
        if obj.musician:
            return f"Musician: {obj.musician.get_full_name() or obj.musician.username}"
        elif obj.instrument_listing:
            return f"Instrument: {obj.instrument_listing.brand} {obj.instrument_listing.model}"
        return "N/A"
    musician_or_instrument.short_description = 'Booking For'
    
    actions = ['mark_as_confirmed', 'mark_as_completed']
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} bookings marked as confirmed.')
    mark_as_confirmed.short_description = 'Mark selected bookings as confirmed'
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} bookings marked as completed.')
    mark_as_completed.short_description = 'Mark selected bookings as completed'

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'reviewee', 'rating', 'booking', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('reviewer__username', 'reviewee__username', 'comment')
    date_hierarchy = 'created_at'
    
    def get_booking_info(self, obj):
        return f"Booking #{obj.booking.id}"
    get_booking_info.short_description = 'Booking'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected notifications as read'

@admin.register(EventApplication)
class EventApplicationAdmin(admin.ModelAdmin):
    list_display = ('musician', 'event', 'proposed_rate', 'status', 'applied_at')
    list_filter = ('status', 'applied_at', 'event__event_type')
    search_fields = ('musician__username', 'musician__first_name', 'musician__last_name', 'event__title')
    date_hierarchy = 'applied_at'
    readonly_fields = ('applied_at', 'updated_at')
    
    fieldsets = (
        ('Application Info', {
            'fields': ('event', 'musician', 'status')
        }),
        ('Details', {
            'fields': ('cover_letter', 'proposed_rate', 'availability_confirmed')
        }),
        ('Organizer Response', {
            'fields': ('organizer_notes',)
        }),
        ('Timestamps', {
            'fields': ('applied_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_musician_name(self, obj):
        return obj.musician.get_full_name() or obj.musician.username
    get_musician_name.short_description = 'Musician'
    
    def get_event_title(self, obj):
        return obj.event.title
    get_event_title.short_description = 'Event'
    
    actions = ['mark_as_accepted', 'mark_as_declined']
    
    def mark_as_accepted(self, request, queryset):
        updated = queryset.update(status='accepted')
        self.message_user(request, f'{updated} applications marked as accepted.')
    mark_as_accepted.short_description = 'Mark selected applications as accepted'
    
    def mark_as_declined(self, request, queryset):
        updated = queryset.update(status='declined')
        self.message_user(request, f'{updated} applications marked as declined.')
    mark_as_declined.short_description = 'Mark selected applications as declined'

# Customize admin site
admin.site.site_header = 'WAFUNGI-NATION Administration'
admin.site.site_title = 'WAFUNGI-NATION Admin'
admin.site.index_title = 'Welcome to WAFUNGI-NATION Administration'
