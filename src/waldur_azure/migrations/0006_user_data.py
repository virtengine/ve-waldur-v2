# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-01-29 16:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('waldur_azure', '0005_ordering'),
    ]

    operations = [
        migrations.AlterField(
            model_name='virtualmachine',
            name='user_data',
            field=models.TextField(blank=True, help_text='Additional data that will be added to instance on provisioning', max_length=87380),
        ),
    ]
