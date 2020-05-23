# Generated by Django 1.11.20 on 2019-06-20 09:51
import django.db.models.deletion
import django.utils.timezone
import django_fsm
import model_utils.fields
from django.db import migrations, models

import waldur_core.core.fields
import waldur_core.core.models
import waldur_core.core.shims
import waldur_core.core.validators
import waldur_core.structure.models


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
        ('waldur_vmware', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='VirtualMachine',
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
                (
                    'created',
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name='created',
                    ),
                ),
                (
                    'modified',
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name='modified',
                    ),
                ),
                (
                    'description',
                    models.CharField(
                        blank=True, max_length=500, verbose_name='description'
                    ),
                ),
                (
                    'name',
                    models.CharField(
                        max_length=150,
                        validators=[waldur_core.core.validators.validate_name],
                        verbose_name='name',
                    ),
                ),
                ('uuid', waldur_core.core.fields.UUIDField()),
                ('error_message', models.TextField(blank=True)),
                (
                    'runtime_state',
                    models.CharField(
                        blank=True, max_length=150, verbose_name='runtime state'
                    ),
                ),
                (
                    'state',
                    django_fsm.FSMIntegerField(
                        choices=[
                            (5, 'Creation Scheduled'),
                            (6, 'Creating'),
                            (1, 'Update Scheduled'),
                            (2, 'Updating'),
                            (7, 'Deletion Scheduled'),
                            (8, 'Deleting'),
                            (3, 'OK'),
                            (4, 'Erred'),
                        ],
                        default=5,
                    ),
                ),
                ('backend_id', models.CharField(blank=True, max_length=255)),
                (
                    'guest_os',
                    models.CharField(
                        help_text='Defines the valid guest operating system types used for configuring a virtual machine',
                        max_length=50,
                    ),
                ),
                (
                    'cores',
                    models.PositiveSmallIntegerField(
                        default=0, help_text='Number of cores in a VM'
                    ),
                ),
                (
                    'cores_per_socket',
                    models.PositiveSmallIntegerField(
                        default=1, help_text='Number of cores per socket in a VM'
                    ),
                ),
                (
                    'ram',
                    models.PositiveIntegerField(
                        default=0, help_text='Memory size in MiB', verbose_name='RAM'
                    ),
                ),
                (
                    'disk',
                    models.PositiveIntegerField(
                        default=0, help_text='Disk size in MiB'
                    ),
                ),
                (
                    'service_project_link',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='+',
                        to='waldur_vmware.VMwareServiceProjectLink',
                    ),
                ),
                (
                    'tags',
                    waldur_core.core.shims.TaggableManager(
                        related_name='+',
                        blank=True,
                        help_text='A comma-separated list of tags.',
                        through='taggit.TaggedItem',
                        to='taggit.Tag',
                        verbose_name='Tags',
                    ),
                ),
            ],
            options={'abstract': False,},
            bases=(
                waldur_core.core.models.DescendantMixin,
                waldur_core.core.models.BackendModelMixin,
                waldur_core.structure.models.StructureLoggableMixin,
                models.Model,
            ),
        ),
    ]
