from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthProfile',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID',
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    'google',
                    models.CharField(
                        max_length=120, unique=True, null=True, blank=True
                    ),
                ),
                (
                    'facebook',
                    models.CharField(
                        max_length=120, unique=True, null=True, blank=True
                    ),
                ),
                (
                    'user',
                    models.OneToOneField(
                        on_delete=models.CASCADE,
                        related_name='auth_profile',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
