from django.shortcuts import render
from .models import Location, WeatherData

# Create your views here.

def index(request):
    """Main page view"""
    locations = Location.objects.all()
    context = {
        'locations': locations,
    }
    return render(request, 'weather/index.html', context)


def location_detail(request, location_id):
    """Detail view for a specific location"""
    location = Location.objects.get(id=location_id)
    weather_data = location.weather_data.all()[:10]  # Get latest 10 records
    context = {
        'location': location,
        'weather_data': weather_data,
    }
    return render(request, 'weather/location_detail.html', context)
