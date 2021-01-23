# Generated by Django 2.2.13 on 2020-10-21 21:47

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.conf import settings
from django.db import migrations, models

import waldur_core.core.fields
import waldur_core.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('uuid', waldur_core.core.fields.UUIDField()),
                (
                    'created',
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False
                    ),
                ),
                (
                    'subject',
                    models.CharField(
                        max_length=1000,
                        validators=[waldur_core.core.validators.validate_name],
                    ),
                ),
                (
                    'body',
                    models.TextField(
                        validators=[waldur_core.core.validators.validate_name]
                    ),
                ),
                ('query', django.contrib.postgres.fields.jsonb.JSONField()),
                ('emails', django.contrib.postgres.fields.jsonb.JSONField()),
                (
                    'author',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={'abstract': False,},
        ),
    ]