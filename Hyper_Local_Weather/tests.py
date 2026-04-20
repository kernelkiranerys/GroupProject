from django.test import TestCase
from django.urls import reverse
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


class PiIngestViewTestCase(TestCase):
    def test_ingest_json_reading(self):
        response = self.client.post(
            reverse('Hyper_Local_Weather:ingest_pi_reading'),
            data='{"timestamp":"2026-04-20T12:00:00Z","device_id":"pi-01","location_name":"Pi Station","latitude":53.8,"longitude":-1.55,"temperature_c":21.5,"humidity":55.2,"pressure_hpa":1012.8,"gas_resistance_ohms":12345.6}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(WeatherReading.objects.count(), 1)
        reading = WeatherReading.objects.first()
        self.assertIsNotNone(reading)
        self.assertEqual(reading.location.name, 'Pi Station')
        self.assertAlmostEqual(reading.temperature_c, 21.5)
        self.assertAlmostEqual(reading.air_quality, 12345.6)
