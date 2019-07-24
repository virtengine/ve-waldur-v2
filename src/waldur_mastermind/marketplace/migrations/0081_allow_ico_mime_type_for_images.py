# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-05-03 06:29
from __future__ import unicode_literals

from django.db import migrations, models
import waldur_core.core.validators
import waldur_core.media.validators


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0080_resource_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='icon',
            field=models.FileField(blank=True, null=True, upload_to='marketplace_category_icons', validators=[
                waldur_core.media.validators.FileTypeValidator(allowed_types=['image/png', 'image/gif', 'image/jpeg', 'image/svg', 'image/svg+xml', 'image/x-icon'])]),
        ),
        migrations.AlterField(
            model_name='offering',
            name='thumbnail',
            field=models.FileField(blank=True, null=True, upload_to='marketplace_service_offering_thumbnails', validators=[
                waldur_core.media.validators.FileTypeValidator(allowed_types=['image/png', 'image/gif', 'image/jpeg', 'image/svg', 'image/svg+xml', 'image/x-icon'])]),
        ),
    ]
