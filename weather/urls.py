from django.urls import path
from . import views

app_name = 'weather'

urlpatterns = [
    path('', views.index, name='index'),
    path('location/<int:location_id>/', views.location_detail, name='location_detail'),
]
