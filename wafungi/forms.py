from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, MusicianProfile, InstrumentListing, Booking, Review, Event, Genre, Instrument

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone = forms.CharField(max_length=15, required=True)
    location = forms.CharField(max_length=100, required=True)
    user_type = forms.ChoiceField(choices=User.USER_TYPES, required=True)
    bio = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    profile_picture = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'location', 'user_type', 'bio', 'profile_picture', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValidationError("Please enter a valid phone number.")
        return phone

class ProfileSetupForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'location', 'bio', 'profile_picture']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }

class MusicianProfileForm(forms.ModelForm):
    genres = forms.ModelMultipleChoiceField(
        queryset=Genre.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    instruments = forms.ModelMultipleChoiceField(
        queryset=Instrument.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = MusicianProfile
        fields = [
            'stage_name', 'genres', 'instruments', 'experience_years',
            'hourly_rate', 'availability_status', 'portfolio_url', 'sample_audio'
        ]
        widgets = {
            'hourly_rate': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'experience_years': forms.NumberInput(attrs={'min': '0'}),
            'portfolio_url': forms.URLInput(attrs={'placeholder': 'https://your-portfolio.com'}),
        }

class EventForm(forms.ModelForm):
    required_genres = forms.ModelMultipleChoiceField(
        queryset=Genre.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    required_instruments = forms.ModelMultipleChoiceField(
        queryset=Instrument.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'event_type', 'date', 'duration_hours',
            'location', 'budget_min', 'budget_max', 'required_genres',
            'required_instruments', 'musicians_needed'
        ]
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'budget_min': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'budget_max': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'duration_hours': forms.NumberInput(attrs={'min': '1', 'max': '24'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        budget_min = cleaned_data.get('budget_min')
        budget_max = cleaned_data.get('budget_max')

        if date and date <= timezone.now():
            raise ValidationError("Event date must be in the future.")

        if budget_min and budget_max and budget_min > budget_max:
            raise ValidationError("Minimum budget cannot be greater than maximum budget.")

        return cleaned_data

class InstrumentListingForm(forms.ModelForm):
    class Meta:
        model = InstrumentListing
        fields = [
            'instrument', 'brand', 'model', 'condition', 'daily_rate',
            'location', 'description', 'image', 'is_available'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'daily_rate': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
        }

    def clean_daily_rate(self):
        daily_rate = self.cleaned_data.get('daily_rate')
        if daily_rate and daily_rate <= 0:
            raise ValidationError("Daily rate must be greater than 0.")
        return daily_rate

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['start_date', 'end_date', 'notes']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and start_date <= timezone.now():
            raise ValidationError("Start date must be in the future.")

        if start_date and end_date and start_date >= end_date:
            raise ValidationError("End date must be after start date.")

        return cleaned_data

class InstrumentRentalForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ('start_date', 'end_date', 'notes')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any special requirements or questions about the rental...'}),
        }
        labels = {
            'start_date': 'Rental Start Date',
            'end_date': 'Rental End Date',
            'notes': 'Additional Notes (Optional)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('start_date', css_class='form-group col-md-6 mb-0'),
                Column('end_date', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'notes',
            Submit('submit', 'Send Rental Request', css_class='btn btn-primary')
        )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date <= start_date:
                raise forms.ValidationError("End date must be after start date.")
            
            # Check if rental period is reasonable (not more than 30 days)
            if (end_date - start_date).days > 30:
                raise forms.ValidationError("Rental period cannot exceed 30 days.")
        
        return cleaned_data

class PaymentForm(forms.Form):
    mpesa_number = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={
            'placeholder': '712345678',
            'pattern': '[0-9]{9}',
            'title': 'Enter 9-digit phone number without country code'
        })
    )

    def clean_mpesa_number(self):
        mpesa_number = self.cleaned_data.get('mpesa_number')
        
        # Remove any non-digit characters
        mpesa_number = ''.join(filter(str.isdigit, mpesa_number))
        
        if len(mpesa_number) != 9:
            raise ValidationError("Please enter a valid 9-digit phone number (e.g., 712345678).")
        
        if not mpesa_number.startswith(('7', '1')):
            raise ValidationError("Phone number should start with 7 or 1.")
        
        return mpesa_number

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share your experience...'}),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating and (rating < 1 or rating > 5):
            raise ValidationError("Rating must be between 1 and 5.")
        return rating

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    subject = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))

    def clean_message(self):
        message = self.cleaned_data.get('message')
        if len(message) < 10:
            raise ValidationError("Message must be at least 10 characters long.")
        return message

class SearchForm(forms.Form):
    q = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search musicians, instruments, events...'})
    )
    genre = forms.ModelChoiceField(
        queryset=Genre.objects.all(),
        required=False,
        empty_label="All Genres"
    )
    instrument = forms.ModelChoiceField(
        queryset=Instrument.objects.all(),
        required=False,
        empty_label="All Instruments"
    )
    location = forms.CharField(max_length=100, required=False)
    min_rate = forms.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Min rate in KSH'})
    )
    max_rate = forms.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Max rate in KSH'})
    )
