# Generated by Django 2.2.13 on 2020-10-08 10:10

from django.db import migrations


def rename_components(apps, schema_editor):
    # fix renaming of components by a previous migration
    OfferingComponent = apps.get_model('marketplace', 'OfferingComponent')
    OfferingComponent.objects.exclude(
        offering__type='SlurmInvoices.SlurmPackage'
    ).filter(name='RAM').update(measured_unit='GB')


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0027_slurm_ram_fixes'),
    ]

    operations = [
        migrations.RunPython(rename_components),
    ]
