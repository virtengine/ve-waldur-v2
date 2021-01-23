# Generated by Django 1.11.21 on 2019-09-09 13:20
from decimal import Decimal

import django.contrib.postgres.fields.jsonb
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import waldur_core.core.fields
import waldur_mastermind.invoices.models
import waldur_mastermind.invoices.utils


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('structure', '0001_squashed_0054'),
        ('packages', '0001_squashed_0015'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
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
                ('uuid', waldur_core.core.fields.UUIDField()),
                (
                    'month',
                    models.PositiveSmallIntegerField(
                        default=waldur_mastermind.invoices.utils.get_current_month,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(12),
                        ],
                    ),
                ),
                (
                    'year',
                    models.PositiveSmallIntegerField(
                        default=waldur_mastermind.invoices.utils.get_current_year
                    ),
                ),
                (
                    'state',
                    models.CharField(
                        choices=[
                            ('pending', 'Pending'),
                            ('created', 'Created'),
                            ('paid', 'Paid'),
                            ('canceled', 'Canceled'),
                        ],
                        default='pending',
                        max_length=30,
                    ),
                ),
                (
                    'customer',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='+',
                        to='structure.Customer',
                        verbose_name='organization',
                    ),
                ),
                (
                    'invoice_date',
                    models.DateField(
                        blank=True,
                        help_text='Date then invoice moved from state pending to created.',
                        null=True,
                    ),
                ),
                (
                    'tax_percent',
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=4,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                    ),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='invoice', unique_together=set([('customer', 'month', 'year')]),
        ),
        migrations.CreateModel(
            name='GenericInvoiceItem',
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
                    'unit_price',
                    models.DecimalField(
                        decimal_places=7,
                        default=0,
                        max_digits=22,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal('0'))
                        ],
                    ),
                ),
                (
                    'unit',
                    models.CharField(
                        choices=[
                            ('month', 'Per month'),
                            ('half_month', 'Per half month'),
                            ('day', 'Per day'),
                            ('hour', 'Per hour'),
                            ('quantity', 'Quantity'),
                        ],
                        default='day',
                        max_length=30,
                    ),
                ),
                ('product_code', models.CharField(blank=True, max_length=30)),
                ('article_code', models.CharField(blank=True, max_length=30)),
                (
                    'start',
                    models.DateTimeField(
                        default=waldur_mastermind.invoices.utils.get_current_month_start,
                        help_text='Date and time when item usage has started.',
                    ),
                ),
                (
                    'end',
                    models.DateTimeField(
                        default=waldur_mastermind.invoices.utils.get_current_month_end,
                        help_text='Date and time when item usage has ended.',
                    ),
                ),
                ('project_name', models.CharField(blank=True, max_length=150)),
                ('project_uuid', models.CharField(blank=True, max_length=32)),
                ('object_id', models.PositiveIntegerField(null=True)),
                (
                    'details',
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=dict, help_text='Stores data about scope'
                    ),
                ),
                (
                    'content_type',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='+',
                        to='contenttypes.ContentType',
                    ),
                ),
                (
                    'invoice',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='generic_items',
                        to='invoices.Invoice',
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to='structure.Project',
                    ),
                ),
                ('quantity', models.PositiveIntegerField(default=0)),
            ],
            options={'abstract': False,},
        ),
        migrations.AddField(
            model_name='invoice',
            name='current_cost',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                editable=False,
                help_text='Cached value for current cost.',
                max_digits=10,
            ),
        ),
        migrations.CreateModel(
            name='ServiceDowntime',
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
                    'start',
                    models.DateTimeField(
                        default=waldur_mastermind.invoices.models.get_default_downtime_start,
                        help_text='Date and time when downtime has started.',
                    ),
                ),
                (
                    'end',
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text='Date and time when downtime has ended.',
                    ),
                ),
                (
                    'package',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to='packages.OpenStackPackage',
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name='invoice',
            name='_file',
            field=models.TextField(blank=True, editable=False),
        ),
    ]