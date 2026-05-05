from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import random

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_pics/', default='Defaults/Default-profile.jpg')
    user_code = models.CharField(max_length=6, unique=True, null=True, blank=True)
    notify_air_quality_alerts = models.BooleanField(default=True)
    notify_temperature_alerts = models.BooleanField(default=True)
    notify_humidity_alerts = models.BooleanField(default=True)
    notify_pressure_alerts = models.BooleanField(default=True)
    notify_positive_weather_alerts = models.BooleanField(default=True)

    @staticmethod
    def generate_unique_user_code():
        while True:
            code = f"{random.randint(0, 999999):06d}"
            if not Profile.objects.filter(user_code=code).exists():
                return code

    def ensure_user_code(self):
        if not self.user_code:
            self.user_code = Profile.generate_unique_user_code()
            self.save(update_fields=['user_code'])

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


class OrganizationInvite(models.Model):
    ROLE_MEMBER = 'member'
    ROLE_STAFF = 'staff'
    ROLE_CHOICES = [
        (ROLE_MEMBER, 'Member'),
        (ROLE_STAFF, 'Staff'),
    ]

    email = models.EmailField()
    code = models.CharField(max_length=6, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_invites')
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_invites')
    accepted_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    @staticmethod
    def generate_unique_code():
        while True:
            code = f"{random.randint(0, 999999):06d}"
            if not OrganizationInvite.objects.filter(code=code).exists():
                return code

    def __str__(self):
        return f"Invite {self.code} for {self.email}"
