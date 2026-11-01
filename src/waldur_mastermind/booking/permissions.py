from rest_framework import exceptions

from waldur_core.core.permissions import has_staff_access
from waldur_core.permissions.enums import PermissionEnum
from waldur_mastermind.marketplace import models
from waldur_mastermind.marketplace.enums import OrderStates, OrderTypes
from waldur_mastermind.marketplace.permissions import has_project_permission


def user_can_reject_order(request, view, resource=None):
    if not resource:
        return

    user = request.user

    if has_staff_access(request):
        return

    try:
        order = models.Order.objects.get(
            resource=resource,
            type=OrderTypes.CREATE,
            state=OrderStates.EXECUTING,
        )
    except models.Order.DoesNotExist:
        return
    except models.Order.MultipleObjectsReturned:
        return

    if user == order.created_by:
        return

    if has_project_permission(
        request, PermissionEnum.REJECT_BOOKING_REQUEST, resource.project
    ):
        return

    raise exceptions.PermissionDenied()
