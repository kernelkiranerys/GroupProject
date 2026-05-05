from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Hyper_Local_Weather', '0007_profile_show_success_notifications_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='show_success_notifications',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='show_tips_notifications',
        ),
        migrations.AddField(
            model_name='profile',
            name='notify_air_quality_alerts',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='notify_humidity_alerts',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='notify_positive_weather_alerts',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='notify_pressure_alerts',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='notify_temperature_alerts',
            field=models.BooleanField(default=True),
        ),
    ]
