# Generated by Django 2.2.13 on 2020-10-07 11:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0024_init_invoice_items_details_from_order_item'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='error_traceback',
            field=models.TextField(blank=True),
        ),
    ]