# Generated by Django 1.11.7 on 2018-01-24 16:24
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('waldur_slurm', '0003_allocationusage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='allocation',
            name='cpu_limit',
            field=models.BigIntegerField(default=-1),
        ),
        migrations.AlterField(
            model_name='allocation',
            name='cpu_usage',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='allocation',
            name='gpu_limit',
            field=models.BigIntegerField(default=-1),
        ),
        migrations.AlterField(
            model_name='allocation',
            name='gpu_usage',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='allocation',
            name='ram_limit',
            field=models.BigIntegerField(default=-1),
        ),
        migrations.AlterField(
            model_name='allocation',
            name='ram_usage',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='allocationusage',
            name='cpu_usage',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='allocationusage',
            name='gpu_usage',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='allocationusage',
            name='ram_usage',
            field=models.BigIntegerField(default=0),
        ),
    ]
