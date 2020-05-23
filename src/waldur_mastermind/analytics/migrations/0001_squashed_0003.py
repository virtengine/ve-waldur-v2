# Generated by Django 1.11.21 on 2019-09-09 13:11
import django.db.models.deletion
from django.db import migrations, models


def import_quotas(apps, schema_editor):
    from waldur_mastermind.analytics.utils import import_daily_usage

    import_daily_usage()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('quotas', '0001_squashed_0004'),
        ('reversion', '0001_squashed_0004_auto_20160611_1202'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyQuotaHistory',
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
                ('object_id', models.PositiveIntegerField(null=True)),
                ('name', models.CharField(db_index=True, max_length=150)),
                ('usage', models.BigIntegerField()),
                ('date', models.DateField()),
                (
                    'content_type',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='contenttypes.ContentType',
                    ),
                ),
            ],
        ),
        migrations.RunPython(import_quotas),
        migrations.AlterField(
            model_name='dailyquotahistory',
            name='content_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='contenttypes.ContentType',
            ),
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
