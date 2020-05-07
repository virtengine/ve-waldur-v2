# Generated by Django 2.2.10 on 2020-05-07 10:23

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('waldur_slurm', '0008_change_limits_default_values'),
    ]

    operations = [
        migrations.CreateModel(
            name='AllocationUserUsage',
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
                ('username', models.CharField(max_length=32)),
                ('cpu_usage', models.BigIntegerField(default=0)),
                ('ram_usage', models.BigIntegerField(default=0)),
                ('gpu_usage', models.BigIntegerField(default=0)),
                (
                    'deposit_usage',
                    models.DecimalField(decimal_places=2, default=0, max_digits=8),
                ),
                (
                    'allocation_usage',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to='waldur_slurm.AllocationUsage',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
