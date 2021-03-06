# Generated by Django 2.2.10 on 2020-04-20 14:09

from django.db import migrations, models

import waldur_core.core.fields


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0014_add_secret_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='offering',
            name='citation_count',
            field=models.IntegerField(
                default=-1, help_text='Number of citations of a DOI'
            ),
        ),
        migrations.AddField(
            model_name='offering',
            name='referred_pids',
            field=waldur_core.core.fields.JSONField(
                blank=True,
                default=dict,
                help_text='List of DOIs referring to the current DOI',
            ),
        ),
    ]
