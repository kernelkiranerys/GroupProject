from django.test import TestCase
from .models import Location, WeatherReading
from django.utils import timezone


class ModelsTestCase(TestCase):
    def test_location_and_reading_creation(self):
        loc = Location.objects.create(name='Test Spot', latitude=12.34567, longitude=54.32123)
        reading = WeatherReading.objects.create(
            location=loc,
            timestamp=timezone.now(),
            temperature_c=22.5,
            humidity=60.0,
            pressure_hpa=1013.25,
        )
        self.assertEqual(loc.readings.count(), 1)
        self.assertEqual(reading.location, loc)
