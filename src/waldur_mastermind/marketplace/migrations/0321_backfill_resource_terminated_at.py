from django.db import migrations

from ._backfill_resource_terminated_at import backfill_resource_terminated_at


class Migration(migrations.Migration):
    # Apart from 0320, as each migration is one transaction: adding the column
    # takes an exclusive lock on marketplace_resource, held until commit, and it
    # must not last as long as this update.
    dependencies = [
        ("marketplace", "0320_resource_terminated_at"),
    ]

    operations = [
        migrations.RunPython(
            backfill_resource_terminated_at, migrations.RunPython.noop
        ),
    ]
