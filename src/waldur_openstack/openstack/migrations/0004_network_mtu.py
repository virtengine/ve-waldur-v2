# Generated by Django 2.2.13 on 2020-10-05 11:55

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openstack', '0003_extend_description_limits'),
    ]

    operations = [
        migrations.AddField(
            model_name='network',
            name='mtu',
            field=models.IntegerField(
                help_text='The maximum transmission unit (MTU) value to address fragmentation.',
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(68),
                    django.core.validators.MaxValueValidator(9000),
                ],
            ),
        ),
    ]