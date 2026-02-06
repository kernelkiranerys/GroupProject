from django.urls import path
from . import views

app_name = 'Hyper_Local_Weather'

urlpatterns = [
    path('', views.index, name='index'),
    path('location/<int:pk>/', views.location_detail, name='location_detail'),
]
