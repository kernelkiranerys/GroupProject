from django.contrib import admin
from django.urls import path, include
from Hyper_Local_Weather import views as weather_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', weather_views.auth_page, name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('Hyper_Local_Weather.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
