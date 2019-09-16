# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-02-12 12:12
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('analytics', '0002_import_quotas'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailyquotahistory',
            name='content_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='dailyquotahistory',
            name='object_id',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterUniqueTogether(
            name='dailyquotahistory',
            unique_together=set([('content_type', 'object_id', 'name', 'date')]),
        ),
    ]
