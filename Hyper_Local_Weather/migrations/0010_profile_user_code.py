from django.db import migrations, models
import random


def backfill_user_codes(apps, schema_editor):
    Profile = apps.get_model('Hyper_Local_Weather', 'Profile')

    existing = set(
        Profile.objects.exclude(user_code__isnull=True)
        .exclude(user_code='')
        .values_list('user_code', flat=True)
    )

    for profile in Profile.objects.all():
        if profile.user_code:
            continue
        while True:
            code = f"{random.randint(0, 999999):06d}"
            if code not in existing:
                existing.add(code)
                profile.user_code = code
                profile.save(update_fields=['user_code'])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('Hyper_Local_Weather', '0009_organizationinvite'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='user_code',
            field=models.CharField(blank=True, max_length=6, null=True, unique=True),
        ),
        migrations.RunPython(backfill_user_codes, migrations.RunPython.noop),
    ]
