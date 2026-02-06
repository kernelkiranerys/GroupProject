from django import forms
from .models import Location, WeatherReading


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['name', 'latitude', 'longitude']


class WeatherReadingForm(forms.ModelForm):
    class Meta:
        model = WeatherReading
        fields = ['location', 'timestamp', 'temperature_c', 'humidity', 'pressure_hpa']
