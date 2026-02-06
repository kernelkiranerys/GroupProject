from django.contrib import admin
from .models import Location, WeatherData

# Register your models here.

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)


@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    list_display = ('location', 'temperature', 'humidity', 'wind_speed', 'recorded_at')
    list_filter = ('location', 'recorded_at')
    search_fields = ('location__name', 'description')
    date_hierarchy = 'recorded_at'
