from django import forms
from django.contrib.auth.forms import UserCreationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from .models import *

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone = forms.CharField(max_length=15, required=False)
    location = forms.CharField(max_length=100, required=False)
    bio = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    profile_picture = forms.ImageField(required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type', 
                 'phone', 'location', 'bio', 'profile_picture', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-0'),
                Column('last_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('username', css_class='form-group col-md-6 mb-0'),
                Column('email', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'user_type',
            Row(
                Column('phone', css_class='form-group col-md-6 mb-0'),
                Column('location', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'bio',
            'profile_picture',
            Row(
                Column('password1', css_class='form-group col-md-6 mb-0'),
                Column('password2', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', 'Register', css_class='btn btn-primary')
        )

class MusicianProfileForm(forms.ModelForm):
    class Meta:
        model = MusicianProfile
        fields = ('stage_name', 'genres', 'instruments', 'experience_years', 
                 'hourly_rate', 'portfolio_url', 'sample_audio')
        widgets = {
            'genres': forms.CheckboxSelectMultiple(),
            'instruments': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'stage_name',
            Row(
                Column('experience_years', css_class='form-group col-md-6 mb-0'),
                Column('hourly_rate', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'genres',
            'instruments',
            'portfolio_url',
            'sample_audio',
            Submit('submit', 'Update Profile', css_class='btn btn-primary')
        )

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ('title', 'description', 'event_type', 'date', 'duration_hours',
                 'location', 'budget_min', 'budget_max', 'required_genres',
                 'required_instruments', 'musicians_needed')
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'required_genres': forms.CheckboxSelectMultiple(),
            'required_instruments': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'title',
            'description',
            Row(
                Column('event_type', css_class='form-group col-md-6 mb-0'),
                Column('date', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('duration_hours', css_class='form-group col-md-4 mb-0'),
                Column('budget_min', css_class='form-group col-md-4 mb-0'),
                Column('budget_max', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            'location',
            'musicians_needed',
            'required_genres',
            'required_instruments',
            Submit('submit', 'Create Event', css_class='btn btn-primary')
        )

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ('start_date', 'end_date', 'notes')
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
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
            Submit('submit', 'Send Booking Request', css_class='btn btn-primary')
        )

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

class InstrumentListingForm(forms.ModelForm):
    class Meta:
        model = InstrumentListing
        fields = ('instrument', 'brand', 'model', 'condition', 'daily_rate',
                 'description', 'image', 'location')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('instrument', css_class='form-group col-md-6 mb-0'),
                Column('condition', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('brand', css_class='form-group col-md-6 mb-0'),
                Column('model', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('daily_rate', css_class='form-group col-md-6 mb-0'),
                Column('location', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'description',
            'image',
            Submit('submit', 'List Instrument', css_class='btn btn-primary')
        )

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
    min_rate = forms.DecimalField(max_digits=8, decimal_places=2, required=False)
    max_rate = forms.DecimalField(max_digits=8, decimal_places=2, required=False)
