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
            'hourly_rate': forms.NumberInput(attrs={'placeholder': 'Enter amount in KSH'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hourly_rate'].help_text = 'Enter your hourly rate in Kenyan Shillings (KSH)'
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
            'budget_min': forms.NumberInput(attrs={'placeholder': 'Minimum budget in KSH'}),
            'budget_max': forms.NumberInput(attrs={'placeholder': 'Maximum budget in KSH'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['budget_min'].help_text = 'Enter minimum budget in Kenyan Shillings (KSH)'
        self.fields['budget_max'].help_text = 'Enter maximum budget in Kenyan Shillings (KSH)'
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

class InstrumentListingForm(forms.ModelForm):
    class Meta:
        model = InstrumentListing
        fields = ('instrument', 'brand', 'model', 'condition', 'daily_rate',
                 'description', 'image', 'location')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'daily_rate': forms.NumberInput(attrs={'placeholder': 'Daily rate in KSH'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['daily_rate'].help_text = 'Enter daily rental rate in Kenyan Shillings (KSH)'
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
