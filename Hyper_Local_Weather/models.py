from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_pics/', default='Defaults/Default-profile.jpg')
    show_tips_notifications = models.BooleanField(default=True)
    show_success_notifications = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

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
    air_quality = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.location.name} @ {self.timestamp.isoformat()}"
