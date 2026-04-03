from django.contrib import admin
from django.urls import path, include
from Hyper_Local_Weather import views as weather_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', weather_views.auth_page, name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('Hyper_Local_Weather.urls')),
]
