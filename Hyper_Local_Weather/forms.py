from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Location, WeatherReading


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['name', 'latitude', 'longitude']


class WeatherReadingForm(forms.ModelForm):
    class Meta:
        model = WeatherReading
        fields = ['location', 'timestamp', 'temperature_c', 'humidity', 'pressure_hpa']


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
