from django.shortcuts import render, get_object_or_404
from .models import Location


def index(request):
    locations = Location.objects.all()
    return render(request, 'Hyper_Local_Weather/index.html', {'locations': locations})


def location_detail(request, pk):
    location = get_object_or_404(Location, pk=pk)
    return render(request, 'Hyper_Local_Weather/location_detail.html', {'location': location})
