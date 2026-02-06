from django.db import models


class Location(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=8, decimal_places=5)
    longitude = models.DecimalField(max_digits=8, decimal_places=5)

    def __str__(self):
        return self.name


class WeatherReading(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='readings')
    timestamp = models.DateTimeField()
    temperature_c = models.FloatField()
    humidity = models.FloatField()
    pressure_hpa = models.FloatField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.location.name} @ {self.timestamp.isoformat()}"
