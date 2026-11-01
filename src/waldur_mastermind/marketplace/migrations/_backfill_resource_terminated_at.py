"""Backfill ``Resource.terminated_at`` for already terminated resources.

The date was not recorded, so it is recovered from what termination leaves behind,
taking the later of:

1. the completion of the latest done Terminate order, unless a done Restore order
   followed it, as then the resource came back and that was not its end;
2. the end of the latest plan period, which closes on termination.

The latest period is taken rather than the greatest end: an open one means the
termination did not close it, and the end of an earlier period marks a plan
switch. The later of the two wins because a resource can be revived and terminated
again with no order at all. Resources with no such evidence stay empty.
``modified`` is no fallback: later saves move it, and a wrong date is worse than
none.

Logic lives here (underscore prefix keeps it out of the migration loader) so it
can be unit-tested. Data migrations run against historical models, hence the
literal states.
"""

from django.db.models import Exists, F, OuterRef, Subquery
from django.db.models.functions import Greatest

RESOURCE_TERMINATED = 6
ORDER_TERMINATE = 3
ORDER_RESTORE = 4
ORDER_DONE = 3


def backfill_resource_terminated_at(apps, schema_editor):
    Resource = apps.get_model("marketplace", "Resource")
    Order = apps.get_model("marketplace", "Order")
    ResourcePlanPeriod = apps.get_model("marketplace", "ResourcePlanPeriod")

    later_restore = Order.objects.filter(
        resource=OuterRef("resource"),
        type=ORDER_RESTORE,
        state=ORDER_DONE,
        completed_at__gt=OuterRef("completed_at"),
    )
    order_completed_at = (
        Order.objects.filter(
            ~Exists(later_restore),
            resource=OuterRef("pk"),
            type=ORDER_TERMINATE,
            state=ORDER_DONE,
            completed_at__isnull=False,
        )
        .order_by("-completed_at")
        .values("completed_at")[:1]
    )
    plan_period_end = (
        ResourcePlanPeriod.objects.filter(resource=OuterRef("pk"))
        .order_by(F("start").desc(nulls_last=True))
        .values("end")[:1]
    )
    # On PostgreSQL, Greatest skips nulls: either source alone is enough.
    Resource.objects.filter(
        state=RESOURCE_TERMINATED, terminated_at__isnull=True
    ).update(
        terminated_at=Greatest(Subquery(order_completed_at), Subquery(plan_period_end))
    )
