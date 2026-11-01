"""Coverage for 0036_mark_credit_compensation_items.

The migration marks every credit compensation `is_compensation`, so it can
still be told from cost once its credit is deleted (`credit` is SET_NULL).
"""

from importlib import import_module

from django.apps import apps as django_apps
from django.test import TestCase

from waldur_mastermind.invoices import utils
from waldur_mastermind.invoices.tests import factories

migration = import_module(
    "waldur_mastermind.invoices.migrations.0036_mark_credit_compensation_items"
)


class MarkCreditCompensationItemsTest(TestCase):
    def setUp(self):
        self.invoice = factories.InvoiceFactory()
        self.credit = factories.CustomerCreditFactory(customer=self.invoice.customer)

    def item(self, name, unit_price, credit=None, details=None):
        return factories.InvoiceItemFactory(
            invoice=self.invoice,
            name=name,
            unit_price=unit_price,
            credit=credit,
            details=details or {},
        )

    def migrate(self):
        migration.mark_credit_compensation_items(django_apps, None)

    def assert_marked(self, item, marked):
        item.refresh_from_db()
        self.assertEqual("is_compensation" in item.details, marked)

    def test_marks_an_item_whose_credit_still_exists(self):
        item = self.item(
            "Credit compensation. VM", -10, self.credit, {"resource_name": "vm"}
        )
        self.migrate()
        self.assert_marked(item, True)
        # The details it copied from the item it pays for are kept.
        self.assertEqual(item.details["resource_name"], "vm")

    def test_marks_an_item_whose_credit_was_deleted(self):
        item = self.item("Credit compensation for 2026-08. VM", -10)
        self.migrate()
        self.assert_marked(item, True)

    def test_leaves_cost_and_discounts_alone(self):
        cost = self.item("VM", 10)
        discount = self.item(
            "Credit compensation-like discount", -5, details={"is_discount": True}
        )
        named_like_compensation = self.item("Credit compensation. VM", 10)
        self.migrate()
        self.assert_marked(cost, False)
        self.assert_marked(discount, False)
        self.assert_marked(named_like_compensation, False)

    def test_marked_items_stay_compensation_once_their_credit_is_deleted(self):
        item = self.item("Credit compensation. VM", -10, self.credit)
        self.migrate()
        self.credit.delete()

        compensations = self.invoice.items.filter(utils.credit_compensation_q())
        self.assertEqual(list(compensations), [item])
        self.assertEqual(
            list(self.invoice.items.exclude(utils.credit_compensation_q())), []
        )
