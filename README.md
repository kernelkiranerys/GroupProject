# GroupProject
Django Hyper Local Weather App

4. Create a superuser to access the admin:

   python manage.py createsuperuser

5. Register the app in settings (already added): 'Hyper_Local_Weather'

6. Run the development server on a custom port (optional):

   python manage.py runserver 8000

#Updating map location

1. marker.setLatLng([newLat, newLon]); (setting marker location)

2. mymap.panTo([newLat, newLon]); (setting camera view)
