from django.utils import timezone

from waldur_mastermind.invoices import registrators
from waldur_mastermind.support import models as support_models
from waldur_mastermind.marketplace import models as marketplace_models

from .utils import is_request_based, component_usage_register

OrderTypes = marketplace_models.OrderItem.Types


def add_new_offering_to_invoice(sender, instance, created=False, **kwargs):
    if created:
        return

    order_item = instance

    if order_item.tracker.has_changed('state') and \
            order_item.state == marketplace_models.OrderItem.States.DONE and \
            order_item.type == marketplace_models.OrderItem.Types.CREATE and \
            order_item.resource and \
            order_item.resource.scope and \
            isinstance(order_item.resource.scope, support_models.Offering) and \
            is_request_based(order_item.resource.scope):
        offering = support_models.Offering.objects.get(pk=order_item.resource.scope.pk)
        registrators.RegistrationManager.register(offering, timezone.now(), order_type=OrderTypes.CREATE)


def terminate_invoice_when_offering_deleted(sender, instance, **kwargs):
    if not is_request_based(instance):
        return

    request_based_offering = support_models.Offering.objects.get(pk=instance.pk)
    registrators.RegistrationManager.terminate(request_based_offering, timezone.now())


def terminate_invoice_when_offering_cancelled(sender, instance, created=False, **kwargs):
    if created:
        return

    if not is_request_based(instance):
        return

    if instance.tracker.has_changed('state') and (instance.state == support_models.Offering.States.TERMINATED):
        request_based_offering = support_models.Offering.objects.get(pk=instance.pk)
        registrators.RegistrationManager.terminate(request_based_offering, timezone.now())


def switch_plan_resource(sender, instance, created=False, **kwargs):
    if created:
        return

    resource = instance
    support_offering = resource.scope

    if not isinstance(support_offering, support_models.Offering):
        return

    if not resource.tracker.has_changed('plan_id'):
        return

    registrators.RegistrationManager.terminate(support_offering, timezone.now())

    if resource.plan.scope:
        support_offering.plan = resource.plan.scope
        support_offering.save(update_fields=['plan'])

    support_offering.unit_price = instance.plan.unit_price
    support_offering.unit = instance.plan.unit
    support_offering.save()

    registrators.RegistrationManager.register(support_offering, timezone.now(), order_type=OrderTypes.UPDATE)


def update_invoice_on_offering_deletion(sender, instance, **kwargs):
    state = instance.state

    if is_request_based(instance):
        return

    if state == support_models.Offering.States.TERMINATED:
        # no need to terminate offering item if it was already terminated before.
        return

    registrators.RegistrationManager.terminate(instance, timezone.now())


def add_new_offering_details_to_invoice(sender, instance, created=False, **kwargs):
    state = instance.state

    if is_request_based(instance):
        return

    if (state == support_models.Offering.States.OK and
            support_models.Offering.States.REQUESTED == instance.tracker.previous('state')):
        registrators.RegistrationManager.register(instance, timezone.now(), order_type=OrderTypes.CREATE)
    if (state == support_models.Offering.States.TERMINATED and
            support_models.Offering.States.OK == instance.tracker.previous('state')):
        registrators.RegistrationManager.terminate(instance, timezone.now())


def add_component_usage(sender, instance, created=False, **kwargs):
    component_usage = instance

    if not created and not component_usage.tracker.has_changed('usage'):
            return

    if not isinstance(component_usage.resource.scope, support_models.Offering):
        return

    component_usage_register(component_usage)
