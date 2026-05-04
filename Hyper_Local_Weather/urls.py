from django.urls import path, include
from weather_project import settings
from django.conf.urls.static import static
from . import views

app_name = 'Hyper_Local_Weather'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/uk-air-quality/', views.uk_air_quality_data, name='uk_air_quality_data'),
    path('api/leeds-air-quality-grid/', views.leeds_air_quality_grid, name='leeds_air_quality_grid'),
    path('api/uk-sensor-hexes/', views.uk_sensor_hex_data, name='uk_sensor_hex_data'),
    path('api/pi-readings/', views.ingest_pi_reading, name='ingest_pi_reading'),
    path('api/gps-location/', views.gps_location, name='gps_location'),
    path('historical/', views.historical, name='historical'),
    path('settings/', views.settings_page, name='settings'),
    path('authorisations/', views.authorisations, name='authorisations'),
    path('location_detail/', views.location_detail, name='location_detail'),
    path('update_location/', views.update_location, name='update_location'),
    path('auth/', views.auth_page, name='auth'),
    path('signup/', views.signup, name='signup'),
    path('<str:date>/', views.index, name='index_with_date'),
    path('location/<int:pk>/', views.location_detail, name='location_detail'),
    path('account/', views.account, name='account'),
    path('update-avatar/', views.update_avatar, name='update_avatar'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)