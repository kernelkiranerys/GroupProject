from django.contrib import admin
from .models import Location, WeatherReading


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude')


@admin.register(WeatherReading)
class WeatherReadingAdmin(admin.ModelAdmin):
    list_display = ('location', 'timestamp', 'temperature_c', 'humidity', 'pressure_hpa')
    list_filter = ('location',)
    date_hierarchy = 'timestamp'
