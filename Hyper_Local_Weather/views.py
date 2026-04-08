import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from .models import Location, WeatherReading
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Avg
from django.contrib.auth import login, authenticate
from django.shortcuts import redirect
from .forms import SignUpForm, ChangeProfileForm, ChangePasswordForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.core.serializers import serialize
from django.contrib.auth.models import User

@login_required
def historical(request):
    readings = WeatherReading.objects.all().order_by('-timestamp')
    context = {
        'readings': readings
    }
    return render(request, 'Hyper_Local_Weather/historical.html', context)

def auth_page(request):
    """Unified authentication page for both login and signup"""
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('Hyper_Local_Weather:index')
    
    signup_form = SignUpForm()
    login_error = None
    signup_error = None
    
    if request.method == 'POST':
        # Check which form was submitted
        if 'login-submit' in request.POST or request.POST.get('action') == 'login':
            # Handle login
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('Hyper_Local_Weather:index')
            else:
                login_error = "Invalid username or password."
        
        elif 'signup-submit' in request.POST or request.POST.get('action') == 'signup':
            # Handle signup
            signup_form = SignUpForm(request.POST)
            if signup_form.is_valid():
                user = signup_form.save()
                login(request, user)
                return redirect('Hyper_Local_Weather:index')
            else:
                signup_error = "Please correct the errors below."
    
    context = {
        'form': None,
        'signup_form': signup_form,
        'login_error': login_error,
        'signup_error': signup_error,
    }
    
    return render(request, 'registration/auth.html', context)

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
    view_mode = request.GET.get('mode', 'outdoor')
    if view_mode not in ('indoor', 'outdoor'):
        view_mode = 'outdoor'

    # MOCK DATA FALLBACKS:
    # Keep these values obvious and centralized so they can be replaced
    # with live sensor/public API data later.
    mock_values = {
        'indoor_temp': 22,
        'outdoor_temp': 23,
        'air_quality': 50,
        'humidity': 63,
        'pressure_hpa': 1013,
    }

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

    # Get latest indoor and outdoor temperatures
    indoor_location = Location.objects.filter(name__icontains='indoor').first()
    outdoor_location = Location.objects.filter(name__icontains='outdoor').first()

    latest_indoor_reading = None
    if indoor_location:
        latest_indoor_reading = WeatherReading.objects.filter(
            location=indoor_location,
            timestamp__date=current_date
        ).order_by('-timestamp').first()

    latest_outdoor_reading = None
    if outdoor_location:
        latest_outdoor_reading = WeatherReading.objects.filter(
            location=outdoor_location,
            timestamp__date=current_date
        ).order_by('-timestamp').first()

    active_reading = latest_indoor_reading if view_mode == 'indoor' else latest_outdoor_reading

    indoor_temp_value = latest_indoor_reading.temperature_c if latest_indoor_reading else mock_values['indoor_temp']
    outdoor_temp_value = latest_outdoor_reading.temperature_c if latest_outdoor_reading else mock_values['outdoor_temp']
    air_quality_value = (
        active_reading.air_quality
        if active_reading and active_reading.air_quality is not None
        else mock_values['air_quality']
    )
    humidity_value = active_reading.humidity if active_reading else mock_values['humidity']
    pressure_value = active_reading.pressure_hpa if active_reading else mock_values['pressure_hpa']

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
        'view_mode': view_mode,
        'latest_indoor_temp': indoor_temp_value,
        'latest_outdoor_temp': outdoor_temp_value,
        'current_air_quality': air_quality_value,
        'current_humidity': humidity_value,
        'current_pressure': pressure_value,
        'is_mock_indoor_temp': latest_indoor_reading is None,
        'is_mock_outdoor_temp': latest_outdoor_reading is None,
        'is_mock_air_quality': active_reading is None or active_reading.air_quality is None,
        'is_mock_humidity': active_reading is None,
        'is_mock_pressure': active_reading is None,
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


@login_required
def settings_page(request):
    profile_form = ChangeProfileForm(instance=request.user)
    password_form = ChangePasswordForm()
    profile_success = profile_error = password_success = password_error = None

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ChangeProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                profile_success = 'Profile updated successfully.'
            else:
                profile_error = 'Please correct the errors below.'

        elif 'change_password' in request.POST:
            password_form = ChangePasswordForm(request.POST)
            if password_form.is_valid():
                if request.user.check_password(password_form.cleaned_data['current_password']):
                    request.user.set_password(password_form.cleaned_data['new_password'])
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    password_success = 'Password changed successfully.'
                    password_form = ChangePasswordForm()
                else:
                    password_error = 'Current password is incorrect.'
            else:
                password_error = 'Please correct the errors below.'

    return render(request, 'Hyper_Local_Weather/settings.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'profile_success': profile_success,
        'profile_error': profile_error,
        'password_success': password_success,
        'password_error': password_error,
    })


@user_passes_test(lambda u: u.is_active and u.is_staff)
def authorisations(request):
    action_success = action_error = None

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        if user_id and action in ('grant', 'revoke'):
            try:
                target = User.objects.get(pk=user_id)
                if action == 'grant':
                    target.is_staff = True
                    target.save()
                    action_success = f"Staff access granted to {target.username}."
                elif target.pk != request.user.pk:
                    target.is_staff = False
                    target.save()
                    action_success = f"Staff access removed from {target.username}."
                else:
                    action_error = "You cannot remove your own staff access."
            except User.DoesNotExist:
                action_error = "User not found."

    users = User.objects.all().order_by('username')
    return render(request, 'Hyper_Local_Weather/authorisations.html', {
        'users': users,
        'action_success': action_success,
        'action_error': action_error,
    })
