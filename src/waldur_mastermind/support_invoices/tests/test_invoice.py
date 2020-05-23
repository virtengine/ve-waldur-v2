import datetime
from decimal import Decimal

from ddt import data, ddt
from django.db.models import Q
from django.utils import timezone
from freezegun import freeze_time
from rest_framework import test

from waldur_core.core import utils as core_utils
from waldur_core.core.utils import month_end
from waldur_mastermind.common.utils import quantize_price
from waldur_mastermind.invoices import models as invoices_models
from waldur_mastermind.invoices import registrators
from waldur_mastermind.invoices.tasks import create_monthly_invoices
from waldur_mastermind.marketplace import callbacks
from waldur_mastermind.marketplace import models as marketplace_models
from waldur_mastermind.marketplace import tasks as marketplace_tasks
from waldur_mastermind.marketplace.tests import factories as marketplace_factories
from waldur_mastermind.support.tests.base import override_support_settings

from . import fixtures


@freeze_time('2018-01-01')
@override_support_settings(
    ENABLED=True, ACTIVE_BACKEND='waldur_mastermind.support.backend.basic:BasicBackend'
)
class InvoicesBaseTest(test.APITransactionTestCase):
    def setUp(self):
        super(InvoicesBaseTest, self).setUp()
        self.fixture = fixtures.SupportFixture()
        self.order_item = self.fixture.order_item

    def order_item_process(self, order_item):
        serialized_order = core_utils.serialize_instance(order_item.order)
        serialized_user = core_utils.serialize_instance(self.fixture.staff)
        marketplace_tasks.process_order(serialized_order, serialized_user)

        order_item.refresh_from_db()
        order_item.order.approve()
        order_item.order.save()

        order_item.resource.scope.set_ok()

    def get_invoice(self):
        date = datetime.date.today()
        return invoices_models.Invoice.objects.get(
            customer=self.fixture.customer, month=date.month, year=date.year,
        )


class InvoicesTest(InvoicesBaseTest):
    def setUp(self):
        super(InvoicesTest, self).setUp()
        self.fixture = fixtures.SupportFixture()
        self.order_item = self.fixture.order_item

    def test_create_invoice(self):
        self.order_item_process(self.order_item)
        invoice = self.get_invoice()
        self.assertEqual(invoice.total, self.fixture.plan.unit_price)
        self.assertEqual(invoice.items.count(), 2)
        self.assertTrue(
            invoice.items.filter(
                details__plan_component_id=self.fixture.plan_component_cpu.id
            ).exists()
        )
        self.assertTrue(
            invoice.items.filter(
                details__plan_component_id=self.fixture.plan_component_ram.id
            ).exists()
        )

    def test_amount_is_multiplied_by_price(self):
        # Arrange
        self.fixture.plan_component_cpu.amount = 0
        self.fixture.plan_component_ram.amount = 0

        self.fixture.plan_component_cpu.save()
        self.fixture.plan_component_ram.save()

        # Act
        self.order_item_process(self.order_item)

        invoice = self.get_invoice()
        self.assertEqual(invoice.total, 0)

    def test_update_invoice_if_added_new_offering(self):
        self.order_item_process(self.order_item)
        self.order_item_process(self.fixture.new_order_item)

        invoice = self.get_invoice()
        self.assertEqual(invoice.total, self.fixture.plan.unit_price * 2)

    def test_terminate_offering(self):
        self.order_item_process(self.order_item)
        offering = self.order_item.resource.scope
        offering.terminate()

        invoice_items = invoices_models.InvoiceItem.objects.filter(scope=offering)

        for item in invoice_items:
            item.refresh_from_db()
            self.assertEqual(item.end, timezone.now())

    def test_delete_offering(self):
        self.order_item_process(self.order_item)
        offering = self.order_item.resource.scope
        invoice_items = invoices_models.InvoiceItem.objects.filter(scope=offering)
        offering.delete()

        for item in invoice_items:
            item.refresh_from_db()
            self.assertEqual(item.end, timezone.now())

    @freeze_time('2018-01-15')
    def test_switch_plan_resource(self):
        self.order_item_process(self.order_item)
        resource = self.order_item.resource
        resource.plan = self.fixture.new_plan
        resource.save()

        new_start = datetime.datetime.now()
        end = month_end(new_start)

        old_items = invoices_models.InvoiceItem.objects.filter(
            project=resource.project, end=new_start,
        )

        unit_price = 0
        self.assertEqual(old_items.count(), 2)

        for i in old_items:
            self.assertTrue(self.fixture.plan.name in i.name)
            unit_price += i.unit_price

        self.assertEqual(unit_price, self.fixture.plan.unit_price)

        new_items = invoices_models.InvoiceItem.objects.filter(
            project=resource.project, start=new_start, end=end,
        )

        unit_price = 0
        self.assertEqual(new_items.count(), 2)

        for i in new_items:
            self.assertTrue(self.fixture.new_plan.name in i.name)
            unit_price += i.unit_price

        self.assertEqual(unit_price, self.fixture.new_plan.unit_price)

    def test_invoice_item_should_include_service_provider_info(self):
        self.order_item_process(self.order_item)
        invoice = self.get_invoice()
        details = invoice.items.first().details
        self.assertTrue('service_provider_name' in details.keys())
        self.assertEqual(
            details['service_provider_name'], self.order_item.offering.customer.name
        )
        self.assertTrue('service_provider_uuid' in details.keys())
        self.assertEqual(
            details['service_provider_uuid'], self.fixture.service_provider.uuid.hex
        )


@ddt
class UsagesTest(InvoicesBaseTest):
    def setUp(self):
        super(UsagesTest, self).setUp()
        self.fixture.offering_component_cpu.billing_type = (
            marketplace_models.OfferingComponent.BillingTypes.USAGE
        )
        self.fixture.offering_component_cpu.save()
        self.fixture.update_plan_prices()

        self.order_item_process(self.order_item)
        self.resource = self.order_item.resource
        self.invoice = self.get_invoice()

    @freeze_time('2018-01-15')
    def test_invoice_price_includes_fixed_and_usage_components(self):
        self.assertEqual(self.invoice.price, self.fixture.plan.unit_price)
        self._create_usage(usage=10)

        self.invoice.refresh_from_db()
        expected = (
            self.fixture.plan_component_ram.price
            * self.fixture.plan_component_ram.amount
            + self.fixture.plan_component_cpu.price * 10
        )
        self.assertEqual(self.invoice.price, expected)

    def test_recurring_usage(self):
        self.fixture.offering_component_ram.delete()

        with freeze_time('2018-01-15'):
            self._create_usage(usage=10, recurring=True)

        with freeze_time('2018-02-01'):
            create_monthly_invoices()
            invoice = invoices_models.Invoice.objects.get(
                customer=self.fixture.customer, month=2, year=2018
            )
            self.assertEqual(marketplace_models.ComponentUsage.objects.count(), 2)
            self.assertEqual(invoice.price, self.fixture.plan_component_cpu.price * 10)

    @freeze_time('2018-01-15')
    def test_new_usage_override_old_usage(self):
        self.assertEqual(self.invoice.price, self.fixture.plan.unit_price)
        usage = self._create_usage(usage=10)
        self.invoice.refresh_from_db()
        expected = (
            self.fixture.plan_component_ram.price
            * self.fixture.plan_component_ram.amount
            + self.fixture.plan_component_cpu.price * 10
        )
        self.assertEqual(self.invoice.price, expected)
        usage.usage = 15
        usage.save()

        self.invoice.refresh_from_db()
        expected = (
            self.fixture.plan_component_ram.price
            * self.fixture.plan_component_ram.amount
            + self.fixture.plan_component_cpu.price * 15
        )
        self.assertEqual(self.invoice.price, expected)

    @freeze_time('2018-01-15')
    def test_case_when_usage_is_reported_for_new_plan(self):
        self.assertEqual(self.invoice.price, self.fixture.plan.unit_price)
        self._switch_plan()
        fixed_price = (
            Decimal(self.fixture.plan.unit_price) * quantize_price(Decimal(15 / 31.0))
        ) + (
            Decimal(self.fixture.new_plan.unit_price)
            * quantize_price(Decimal(17 / 31.0))
        )
        self.assertEqual(self.invoice.price, fixed_price)
        self._create_usage(usage=10)

        self.invoice.refresh_from_db()
        self.assertEqual(
            self.invoice.price,
            fixed_price + self.fixture.new_plan_component_cpu.price * 10,
        )

    @freeze_time('2018-01-15')
    def test_case_when_usage_is_reported_for_switched_plan(self):
        self.assertEqual(self.invoice.price, self.fixture.plan.unit_price)
        self._switch_plan()
        fixed_price = (
            Decimal(self.fixture.plan.unit_price) * quantize_price(Decimal(15 / 31.0))
        ) + (
            Decimal(self.fixture.new_plan.unit_price)
            * quantize_price(Decimal(17 / 31.0))
        )
        self.assertEqual(self.invoice.price, fixed_price)
        self._create_usage(datetime.date(2018, 1, 10), usage=10)

        self.invoice.refresh_from_db()
        self.assertEqual(
            self.invoice.price, fixed_price + self.fixture.plan_component_cpu.price * 10
        )

    @freeze_time('2018-01-15')
    @data(5, 10, 20)
    def test_update_usage_component_amount(self, new_amount):
        self.assertEqual(self.invoice.price, self.fixture.plan.unit_price)
        component_usage = self._create_usage(usage=10)
        component_usage.usage = new_amount
        component_usage.save()

        self.invoice.refresh_from_db()
        self.assertEqual(
            self.invoice.price,
            self.fixture.plan_component_ram.price
            * self.fixture.plan_component_ram.amount
            + self.fixture.plan_component_cpu.price * new_amount,
        )

    def test_invoice_item_name_includes_component_name(self):
        self._create_usage(usage=10)
        invoice_item_name = self.invoice.items.last().name
        self.assertTrue(self.fixture.offering_component_cpu.name in invoice_item_name)

    def test_invoice_item_name_includes_resource_name(self):
        self._create_usage(usage=10)
        invoice_item_name = self.invoice.items.last().name
        self.assertTrue(self.resource.name in invoice_item_name)

    def _switch_plan(self):
        marketplace_factories.OrderItemFactory(
            resource=self.resource,
            type=marketplace_models.RequestTypeMixin.Types.UPDATE,
            state=marketplace_models.OrderItem.States.EXECUTING,
            plan=self.fixture.new_plan,
        )
        callbacks.resource_update_succeeded(self.resource)
        self.invoice.refresh_from_db()

    def _create_usage(self, date=None, **kwargs):
        date = date or datetime.date.today()
        plan_period = (
            marketplace_models.ResourcePlanPeriod.objects.filter(
                Q(start__lte=date) | Q(start__isnull=True)
            )
            .filter(Q(end__gt=date) | Q(end__isnull=True))
            .get(resource=self.resource)
        )
        option = dict(
            resource=self.resource,
            component=self.fixture.offering_component_cpu,
            usage=10,
            date=date,
            billing_period=core_utils.month_start(date),
            plan_period=plan_period,
        )
        option.update(kwargs)
        return marketplace_models.ComponentUsage.objects.create(**option)


class OneTimeTest(InvoicesBaseTest):
    def setUp(self):
        super(OneTimeTest, self).setUp()
        self.fixture.offering_component_cpu.billing_type = (
            marketplace_models.OfferingComponent.BillingTypes.ONE_TIME
        )
        self.fixture.offering_component_cpu.save()
        self.fixture.update_plan_prices()

        self.order_item_process(self.order_item)
        self.resource = self.order_item.resource
        self.invoice = self.get_invoice()

    @freeze_time('2018-01-01')
    def test_calculate_one_time_component_if_resource_started_in_current_period(self):
        self.invoice.refresh_from_db()
        expected = (
            self.fixture.plan_component_cpu.price
            * self.fixture.plan_component_cpu.amount
            + self.fixture.plan_component_ram.price
            * self.fixture.plan_component_ram.amount
        )
        self.assertEqual(self.invoice.price, expected)

    @freeze_time('2018-02-01')
    def test_do_not_calculate_one_time_component_if_resource_started_not_in_current_period(
        self,
    ):
        registrators.RegistrationManager.register(self.resource.scope)
        self.invoice = self.get_invoice()
        expected = (
            self.fixture.plan_component_ram.price
            * self.fixture.plan_component_ram.amount
        )
        self.assertEqual(self.invoice.price, expected)


class OnPlanSwitchTest(InvoicesBaseTest):
    def setUp(self):
        super(OnPlanSwitchTest, self).setUp()
        self.fixture.offering_component_cpu.billing_type = (
            marketplace_models.OfferingComponent.BillingTypes.ON_PLAN_SWITCH
        )
        self.fixture.offering_component_cpu.save()
        self.fixture.update_plan_prices()

        self.order_item_process(self.order_item)
        self.resource = self.order_item.resource
        self.invoice = self.get_invoice()

    @freeze_time('2018-02-01')
    def test_do_not_calculate_on_plan_switch_component_if_resource_started_not_in_current_period(
        self,
    ):
        registrators.RegistrationManager.register(self.resource.scope)
        self.invoice = self.get_invoice()
        expected = (
            self.fixture.plan_component_ram.price
            * self.fixture.plan_component_ram.amount
        )
        self.assertEqual(self.invoice.price, expected)

    @freeze_time('2018-03-01')
    def test_calculate_on_plan_switch_component_if_plan_has_been_switched_in_current_period(
        self,
    ):
        order_item = marketplace_factories.OrderItemFactory(
            type=marketplace_models.OrderItem.Types.UPDATE,
            resource=self.resource,
            plan=self.fixture.plan,
        )
        order_item.set_state_executing()
        order_item.set_state_done()
        order_item.save()
        registrators.RegistrationManager.register(
            self.resource.scope,
            timezone.now(),
            order_type=marketplace_models.OrderItem.Types.UPDATE,
        )
        self.invoice = self.get_invoice()
        expected = (
            self.fixture.plan_component_cpu.price
            * self.fixture.plan_component_cpu.amount
            + self.fixture.plan_component_ram.price
            * self.fixture.plan_component_ram.amount
        )
        self.assertEqual(self.invoice.price, expected)


class LimitUsageTest(InvoicesBaseTest):
    def setUp(self):
        super(LimitUsageTest, self).setUp()
        self.fixture.offering_component_cpu.billing_type = (
            marketplace_models.OfferingComponent.BillingTypes.USAGE
        )
        self.fixture.offering_component_cpu.use_limit_for_billing = True
        self.fixture.offering_component_cpu.save()
        self.fixture.update_plan_prices()

        self.order_item.limits = {self.fixture.offering_component_cpu.type: 16}
        self.order_item.save()

    def test_charge_is_based_on_limit(self):
        self.order_item_process(self.order_item)
        self.resource = self.order_item.resource
        self.invoice = self.get_invoice()
        expected = (
            self.fixture.plan_component_cpu.price * 16
            + self.fixture.plan_component_ram.price
            * self.fixture.plan_component_ram.amount
        )
        self.assertEqual(self.invoice.price, expected)
