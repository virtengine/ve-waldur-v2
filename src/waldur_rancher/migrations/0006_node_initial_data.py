# Generated by Django 2.2.7 on 2019-11-26 11:36

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('waldur_rancher', '0005_node_name_is_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='node',
            name='initial_data',
            field=django.contrib.postgres.fields.jsonb.JSONField(
                blank=True,
                default=dict,
                help_text='Initial data for instance creating.',
            ),
        ),
    ]
