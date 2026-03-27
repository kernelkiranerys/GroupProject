import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from .models import Location, WeatherReading
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Avg
from django.contrib.auth import login
from django.shortcuts import redirect
from .forms import SignUpForm
from django.contrib.auth.decorators import login_required
from django.core.serializers import serialize

@login_required
def historical(request):
    readings = WeatherReading.objects.all().order_by('-timestamp')
    context = {
        'readings': readings
    }
    return render(request, 'Hyper_Local_Weather/historical.html', context)

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('Hyper_Local_Weather:index')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

def index(request, date=None):
    locations = Location.objects.all()
    locations_with_readings = []
    for loc in locations:
        latest_reading = WeatherReading.objects.filter(location=loc).order_by('-timestamp').first()
        locations_with_readings.append({
            'pk': loc.pk,
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'latest_reading': {
                'air_quality': latest_reading.air_quality if latest_reading else None
            }
        })

    if date:
        current_date = datetime.strptime(date, '%Y-%m-%d').date()
    else:
        current_date = timezone.now().date()

    # Get latest indoor temperature
    indoor_location = Location.objects.filter(name__icontains='indoor').first()
    latest_indoor_reading = None
    if indoor_location:
        latest_indoor_reading = WeatherReading.objects.filter(
            location=indoor_location,
            timestamp__date=current_date
        ).order_by('-timestamp').first()

    past_week_temps = []
    for i in range(6, -1, -1):
        day = current_date - timedelta(days=i)
        avg_temp_data = WeatherReading.objects.filter(timestamp__date=day).aggregate(avg_temp=Avg('temperature_c'))
        
        avg_temp = avg_temp_data['avg_temp']
        
        past_week_temps.append({
            'day_name': day.strftime('%a')[0],
            'avg_temp': round(avg_temp) if avg_temp is not None else 'N/A'
        })

    previous_week = current_date - timedelta(weeks=1)
    next_week = current_date + timedelta(weeks=1)

    is_current_week = next_week > timezone.now().date()


    context = {
        'locations': locations_with_readings,
        'latest_indoor_temp': latest_indoor_reading.temperature_c if latest_indoor_reading else 'N/A',
        'past_week_temps': past_week_temps,
        'current_date': current_date,
        'previous_week': previous_week.strftime('%Y-%m-%d'),
        'next_week': next_week.strftime('%Y-%m-%d'),
        'is_current_week': is_current_week,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'past_week_temps': past_week_temps,
            'current_date': current_date.strftime('%b %d, %Y'),
            'previous_week': previous_week.strftime('%Y-%m-%d'),
            'next_week': next_week.strftime('%Y-%m-%d'),
            'is_current_week': is_current_week,
        })

    return render(request, 'Hyper_Local_Weather/index.html', context)

# AJAX endpoint to update location
@csrf_exempt
def update_location(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            location = {
                'lat': data.get('lat'),
                'lon': data.get('lon')
            }
            request.session['location'] = location
            return JsonResponse({'status': 'success', 'location': location})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


def location_detail(request, pk):
    location = get_object_or_404(Location, pk=pk)
    return render(request, 'Hyper_Local_Weather/location_detail.html', {'location': location})
