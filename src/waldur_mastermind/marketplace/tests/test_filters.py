from rest_framework import test

from waldur_core.structure.tests import factories as structure_factories
from waldur_core.structure.tests import fixtures as structure_fixtures
from waldur_mastermind.marketplace.tests import factories


class CustomerResourcesFilterTest(test.APITransactionTestCase):
    def setUp(self):
        self.fixture1 = structure_fixtures.ServiceFixture()
        self.customer1 = self.fixture1.customer
        self.offering = factories.OfferingFactory(customer=self.customer1)
        self.resource1 = factories.ResourceFactory(
            offering=self.offering, project=self.fixture1.project
        )

        self.fixture2 = structure_fixtures.ServiceFixture()
        self.customer2 = self.fixture2.customer

    def list_customers(self, has_resources):
        list_url = structure_factories.CustomerFactory.get_list_url()
        self.client.force_authenticate(self.fixture1.staff)
        if has_resources:
            return self.client.get(list_url, {'has_resources': has_resources}).data
        else:
            return self.client.get(list_url).data

    def test_list_customers_with_resources(self):
        self.assertEqual(1, len(self.list_customers(True)))

    def test_list_all_customers(self):
        self.assertEqual(2, len(self.list_customers(False)))


class ServiceProviderFilterTest(test.APITransactionTestCase):
    def setUp(self):
        self.fixture1 = structure_fixtures.ServiceFixture()
        self.service_provider1 = self.fixture1.customer
        self.offering1 = factories.OfferingFactory(customer=self.service_provider1)
        self.resource1 = factories.ResourceFactory(
            offering=self.offering1, project=self.fixture1.project
        )

        self.fixture2 = structure_fixtures.ServiceFixture()
        self.service_provider2 = self.fixture2.customer
        factories.OfferingFactory(customer=self.service_provider2)

    def list_customers(self, service_provider_uuid):
        list_url = structure_factories.CustomerFactory.get_list_url()
        self.client.force_authenticate(self.fixture1.staff)
        return self.client.get(
            list_url, {'service_provider_uuid': service_provider_uuid}
        ).data

    def test_list_offering_customers(self):
        customers = self.list_customers(self.service_provider1.uuid.hex)
        self.assertEqual(1, len(customers))
        self.assertEqual(customers[0]['uuid'], self.resource1.project.customer.uuid.hex)

    def test_list_is_empty_if_offering_does_not_have_customers(self):
        self.assertEqual(0, len(self.list_customers(self.service_provider2.uuid.hex)))
