from django.shortcuts import render, get_object_or_404
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
    location = get_object_or_404(Location, id=location_id)
    weather_data = location.weather_data.order_by('-recorded_at')[:10]  # Get latest 10 records
    context = {
        'location': location,
        'weather_data': weather_data,
    }
    return render(request, 'weather/location_detail.html', context)
