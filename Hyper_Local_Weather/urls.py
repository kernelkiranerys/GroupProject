from django.urls import path, include
from . import views

app_name = 'Hyper_Local_Weather'

urlpatterns = [
    path('', views.index, name='index'),
    path('historical/', views.historical, name='historical'),
    path('location_detail/', views.location_detail, name='location_detail'),
    path('update_location/', views.update_location, name='update_location'),
    path('auth/', views.auth_page, name='auth'),
    path('signup/', views.signup, name='signup'),
    path('<str:date>/', views.index, name='index_with_date'),
    path('location/<int:pk>/', views.location_detail, name='location_detail'),
]