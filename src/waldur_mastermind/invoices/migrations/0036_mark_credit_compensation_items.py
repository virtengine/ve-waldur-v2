from django.db import migrations
from django.db.models import Q

BATCH_SIZE = 1000


def mark_credit_compensation_items(apps, schema_editor):
    """Mark every credit compensation `is_compensation`.

    The marker is younger than many invoices, and `credit` is `SET_NULL`, so a
    compensation whose credit was deleted had nothing left to tell it from
    negative cost. Such an item is still found by its name: every writer has
    named it "Credit compensation…", as 0013 relied on. The name matters: other
    lines are negative too (discounts, one-time limit decreases, staff refunds).
    """
    InvoiceItem = apps.get_model("invoices", "InvoiceItem")
    items = (
        InvoiceItem.objects.filter(
            Q(credit__isnull=False)
            | Q(name__startswith="Credit compensation", unit_price__lt=0)
        )
        .exclude(details__has_key="is_compensation")
        .exclude(details__has_key="is_discount")
        .only("pk", "details")
    )
    batch = []
    for item in items.iterator(chunk_size=BATCH_SIZE):
        item.details = {**(item.details or {}), "is_compensation": True}
        batch.append(item)
        if len(batch) >= BATCH_SIZE:
            InvoiceItem.objects.bulk_update(batch, ["details"])
            batch = []
    if batch:
        InvoiceItem.objects.bulk_update(batch, ["details"])


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0035_project_credit_compensate_in"),
    ]

    operations = [
        migrations.RunPython(mark_credit_compensation_items, migrations.RunPython.noop),
    ]
