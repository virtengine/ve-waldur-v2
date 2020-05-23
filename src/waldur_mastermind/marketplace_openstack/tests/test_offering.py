import uuid
from unittest import mock

from ddt import data, ddt
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status, test

from waldur_core.core.tests.helpers import override_waldur_core_settings
from waldur_core.structure import models as structure_models
from waldur_core.structure.tests import factories as structure_factories
from waldur_core.structure.tests import fixtures as structure_fixtures
from waldur_mastermind.common.mixins import UnitPriceMixin
from waldur_mastermind.marketplace import models as marketplace_models
from waldur_mastermind.marketplace.management.commands.load_categories import (
    load_category,
)
from waldur_mastermind.marketplace.tests import factories as marketplace_factories
from waldur_mastermind.marketplace_openstack import (
    CORES_TYPE,
    RAM_TYPE,
    STORAGE_MODE_DYNAMIC,
    STORAGE_MODE_FIXED,
    STORAGE_TYPE,
)
from waldur_mastermind.marketplace_openstack.utils import (
    create_offering_components,
    merge_plans,
)
from waldur_mastermind.packages import models as package_models
from waldur_mastermind.packages.tests import fixtures as package_fixtures
from waldur_openstack.openstack import models as openstack_models
from waldur_openstack.openstack.tests import fixtures as openstack_fixtures

from .. import INSTANCE_TYPE, PACKAGE_TYPE, VOLUME_TYPE
from .utils import BaseOpenStackTest, override_plugin_settings


class VpcExternalFilterTest(BaseOpenStackTest):
    def setUp(self):
        super(VpcExternalFilterTest, self).setUp()
        self.fixture = package_fixtures.OpenStackFixture()
        self.offering = marketplace_factories.OfferingFactory(
            category=self.tenant_category
        )
        self.url = marketplace_factories.OfferingFactory.get_list_url()

    @override_waldur_core_settings(ONLY_STAFF_MANAGES_SERVICES=True)
    def test_staff_can_see_vpc_offering(self):
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.get(self.url)
        self.assertEqual(1, len(response.data))

    @override_waldur_core_settings(ONLY_STAFF_MANAGES_SERVICES=True)
    def test_other_users_can_not_see_vpc_offering_if_feature_is_enabled(self):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.get(self.url)
        self.assertEqual(0, len(response.data))

    @override_waldur_core_settings(ONLY_STAFF_MANAGES_SERVICES=False)
    def test_other_users_can_see_vpc_offering_if_feature_is_disabled(self):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.get(self.url)
        self.assertEqual(1, len(response.data))


class TemplateOfferingTest(BaseOpenStackTest):
    def test_template_for_plan_is_created(self):
        fixture = package_fixtures.OpenStackFixture()
        offering = marketplace_factories.OfferingFactory(
            type=PACKAGE_TYPE, scope=fixture.openstack_service_settings
        )
        plan = marketplace_factories.PlanFactory(offering=offering)
        ram_component = marketplace_models.OfferingComponent.objects.create(
            offering=offering, type=RAM_TYPE,
        )
        marketplace_models.PlanComponent.objects.create(
            plan=plan, component=ram_component, amount=20, price=10,
        )

        cores_component = marketplace_models.OfferingComponent.objects.create(
            offering=offering, type=CORES_TYPE,
        )
        marketplace_models.PlanComponent.objects.create(
            plan=plan, component=cores_component, amount=10, price=3,
        )

        storage_component = marketplace_models.OfferingComponent.objects.create(
            offering=offering, type=STORAGE_TYPE,
        )
        marketplace_models.PlanComponent.objects.create(
            plan=plan, component=storage_component, amount=100, price=1,
        )
        plan.refresh_from_db()

        template = plan.scope
        self.assertTrue(isinstance(template, package_models.PackageTemplate))

        template_ram_component = template.components.get(type=RAM_TYPE)
        template_cores_component = template.components.get(type=CORES_TYPE)
        template_storage_component = template.components.get(type=STORAGE_TYPE)

        self.assertEqual(template_ram_component.amount, 20 * 1024)
        self.assertEqual(template_ram_component.price, 10.0 / 1024)

        self.assertEqual(template_cores_component.amount, 10)
        self.assertEqual(template_cores_component.price, 3)

        self.assertEqual(template_storage_component.amount, 100 * 1024)
        self.assertEqual(template_storage_component.price, 1.0 / 1024)

    def test_template_for_plan_is_not_created_if_type_is_invalid(self):
        offering = marketplace_factories.OfferingFactory(type='INVALID')
        plan = marketplace_factories.PlanFactory(offering=offering)
        plan.refresh_from_db()
        self.assertIsNone(plan.scope)

    def test_when_plan_is_archived_template_is_updated(self):
        # Arrange
        fixture = package_fixtures.OpenStackFixture()
        offering = marketplace_factories.OfferingFactory(
            type=PACKAGE_TYPE, scope=fixture.openstack_service_settings
        )
        plan = marketplace_factories.PlanFactory(offering=offering)
        plan.refresh_from_db()

        # Act
        plan.archived = True
        plan.save()
        template = plan.scope

        # Assert
        self.assertTrue(template.archived)

    def test_when_plan_is_unarchived_template_is_updated(self):
        # Arrange
        fixture = package_fixtures.OpenStackFixture()
        offering = marketplace_factories.OfferingFactory(
            type=PACKAGE_TYPE, scope=fixture.openstack_service_settings
        )
        plan = marketplace_factories.PlanFactory(offering=offering, archived=True)
        plan.refresh_from_db()

        # Act
        plan.archived = False
        plan.save()
        template = plan.scope

        # Assert
        self.assertFalse(template.archived)

    def test_when_plan_name_is_updated_template_is_updated(self):
        # Arrange
        fixture = package_fixtures.OpenStackFixture()
        offering = marketplace_factories.OfferingFactory(
            type=PACKAGE_TYPE, scope=fixture.openstack_service_settings
        )
        plan = marketplace_factories.PlanFactory(offering=offering)
        plan.refresh_from_db()

        # Act
        plan.name = 'Compute-intensive'
        plan.save()
        template = plan.scope

        # Assert
        self.assertEqual(template.name, plan.name)

    def test_when_template_is_archived_plan_is_updated(self):
        # Arrange
        fixture = package_fixtures.OpenStackFixture()
        offering = marketplace_factories.OfferingFactory(
            type=PACKAGE_TYPE, scope=fixture.openstack_service_settings
        )
        plan = marketplace_factories.PlanFactory(offering=offering)
        plan.refresh_from_db()
        template = plan.scope

        # Act
        template.archived = True
        template.save()
        plan.refresh_from_db()

        # Assert
        self.assertTrue(plan.archived)

    def test_when_template_is_unarchived_template_is_updated(self):
        # Arrange
        fixture = package_fixtures.OpenStackFixture()
        offering = marketplace_factories.OfferingFactory(
            type=PACKAGE_TYPE, scope=fixture.openstack_service_settings
        )
        plan = marketplace_factories.PlanFactory(offering=offering, archived=True)
        plan.refresh_from_db()
        template = plan.scope

        # Act
        template.archived = False
        template.save()
        plan.refresh_from_db()

        # Assert
        self.assertFalse(plan.archived)

    def test_when_template_name_is_updated_template_is_synchronized(self):
        # Arrange
        fixture = package_fixtures.OpenStackFixture()
        offering = marketplace_factories.OfferingFactory(
            type=PACKAGE_TYPE, scope=fixture.openstack_service_settings
        )
        plan = marketplace_factories.PlanFactory(offering=offering)
        plan.refresh_from_db()
        template = plan.scope

        # Act
        template.name = 'Compute-intensive'
        template.save()
        plan.refresh_from_db()

        # Assert
        self.assertEqual(plan.name, template.name)


class PlanComponentsTest(test.APITransactionTestCase):
    prices = {
        'cores': 10,
        'ram': 100,
        'storage': 1000,
    }
    quotas = prices

    def setUp(self):
        super(PlanComponentsTest, self).setUp()
        self.category = load_category('vpc')

    def test_plan_components_are_validated(self):
        response = self.create_offering()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        offering = marketplace_models.Offering.objects.get(uuid=response.data['uuid'])
        self.assertEqual(offering.plans.first().components.count(), 3)

    def test_plan_components_have_parent(self):
        response = self.create_offering()
        offering = marketplace_models.Offering.objects.get(uuid=response.data['uuid'])
        self.assertEqual(3, offering.components.exclude(parent=None).count())

    def test_plan_without_components_is_valid(self):
        response = self.create_offering(False)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_total_price_is_calculated_from_components(self):
        response = self.create_offering()
        offering = marketplace_models.Offering.objects.get(uuid=response.data['uuid'])
        self.assertEqual(
            offering.plans.first().unit_price, 10 * 10 + 100 * 100 + 1000 * 1000
        )

    def test_plan_components_are_updated(self):
        response = self.create_offering()
        offering = marketplace_models.Offering.objects.get(uuid=response.data['uuid'])
        component = offering.plans.first().components.get(component__type='cores')
        component.amount += 1
        component.save()
        template = package_models.PackageTemplate.objects.get(
            service_settings=offering.scope
        )
        self.assertEqual(template.components.get(type='cores').amount, component.amount)

    def create_offering(self, components=True):
        fixture = structure_fixtures.ProjectFixture()
        url = marketplace_factories.OfferingFactory.get_list_url()
        self.client.force_authenticate(fixture.owner)
        payload = {
            'name': 'offering',
            'category': marketplace_factories.CategoryFactory.get_url(self.category),
            'customer': structure_factories.CustomerFactory.get_url(fixture.customer),
            'type': PACKAGE_TYPE,
            'service_attributes': {
                'backend_url': 'http://example.com/',
                'username': 'root',
                'password': 'secret',
                'tenant_name': 'admin',
                'external_network_id': uuid.uuid4(),
            },
            'plans': [
                {
                    'name': 'small',
                    'description': 'CPU 1',
                    'unit': UnitPriceMixin.Units.PER_DAY,
                    'unit_price': 1010100,
                }
            ],
        }
        if components:
            payload['plans'][0]['prices'] = self.prices
            payload['plans'][0]['quotas'] = self.quotas
        with mock.patch('waldur_core.structure.models.ServiceSettings.get_backend'):
            return self.client.post(url, payload)


@ddt
class OpenStackResourceOfferingTest(BaseOpenStackTest):
    @data(INSTANCE_TYPE, VOLUME_TYPE)
    def test_offering_is_created_when_tenant_creation_is_completed(self, offering_type):
        tenant = self.trigger_offering_creation()

        offering = marketplace_models.Offering.objects.get(type=offering_type)
        service_settings = offering.scope

        self.assertTrue(isinstance(service_settings, structure_models.ServiceSettings))
        self.assertEqual(service_settings.scope, tenant)

    @data(INSTANCE_TYPE, VOLUME_TYPE)
    @override_plugin_settings(AUTOMATICALLY_CREATE_PRIVATE_OFFERING=False)
    def test_offering_is_not_created_if_feature_is_disabled(self, offering_type):
        self.trigger_offering_creation()

        self.assertRaises(
            marketplace_models.Offering.DoesNotExist,
            lambda: marketplace_models.Offering.objects.get(type=offering_type),
        )

    @data(INSTANCE_TYPE, VOLUME_TYPE)
    def test_offering_is_not_created_if_tenant_is_not_created_via_marketplace(
        self, offering_type
    ):
        fixture = package_fixtures.OpenStackFixture()
        tenant = openstack_models.Tenant.objects.create(
            service_project_link=fixture.openstack_spl,
            state=openstack_models.Tenant.States.CREATING,
        )

        tenant.set_ok()
        tenant.save()

        self.assertRaises(
            ObjectDoesNotExist,
            marketplace_models.Offering.objects.get,
            type=offering_type,
        )

    @data(INSTANCE_TYPE, VOLUME_TYPE)
    def test_offering_is_archived_when_tenant_is_deleted(self, offering_type):
        tenant = self.trigger_offering_creation()
        tenant.delete()
        offering = marketplace_models.Offering.objects.get(type=offering_type)
        self.assertEqual(offering.state, marketplace_models.Offering.States.ARCHIVED)

    def trigger_offering_creation(self):
        fixture = package_fixtures.OpenStackFixture()
        tenant = openstack_models.Tenant.objects.create(
            service_project_link=fixture.openstack_spl,
            state=openstack_models.Tenant.States.CREATING,
        )
        resource = marketplace_factories.ResourceFactory(scope=tenant)
        marketplace_factories.OrderItemFactory(resource=resource)

        tenant.set_ok()
        tenant.save()
        return tenant


class MergePlansTest(test.APITransactionTestCase):
    def setUp(self):
        fixture = package_fixtures.OpenStackFixture()
        offering = marketplace_factories.OfferingFactory(
            type=PACKAGE_TYPE, scope=fixture.openstack_service_settings
        )
        create_offering_components(offering)
        for name in 'Basic', 'Advanced':
            plan = marketplace_factories.PlanFactory(offering=offering, name=name)
            prices = {
                CORES_TYPE: 1,
                RAM_TYPE: 0.1,
                STORAGE_TYPE: 0.01,
            }
            for key, value in prices.items():
                component = marketplace_models.OfferingComponent.objects.get(
                    offering=offering, type=key,
                )
                marketplace_models.PlanComponent.objects.create(
                    plan=plan, component=component, price=value,
                )
            resource = marketplace_factories.ResourceFactory(
                offering=offering, plan=plan,
            )
            marketplace_factories.OrderItemFactory(
                offering=offering, plan=plan, resource=resource,
            )
        self.offering = offering

    def test_plans_are_merged(self):
        merge_plans(self.offering, self.offering.plans.first())
        self.assertEqual(self.offering.plans.count(), 1)
        self.assertEqual(self.offering.plans.get().name, 'Default')
        self.assertEqual(
            marketplace_models.Resource.objects.filter(offering=self.offering).count(),
            2,
        )
        self.assertEqual(
            marketplace_models.OrderItem.objects.filter(offering=self.offering).count(),
            2,
        )


class OfferingComponentForVolumeTypeTest(test.APITransactionTestCase):
    def setUp(self) -> None:
        self.fixture = openstack_fixtures.OpenStackFixture()
        self.offering = marketplace_factories.OfferingFactory(
            type=PACKAGE_TYPE, scope=self.fixture.openstack_service_settings
        )
        self.volume_type = self.fixture.volume_type

    def test_offering_component_for_volume_type_is_created(self):
        component = marketplace_models.OfferingComponent.objects.get(
            scope=self.volume_type
        )
        self.assertEqual(component.offering, self.offering)
        self.assertEqual(
            component.billing_type,
            marketplace_models.OfferingComponent.BillingTypes.USAGE,
        )
        self.assertEqual(component.name, 'Storage (%s)' % self.volume_type.name)
        self.assertEqual(component.type, 'gigabytes_' + self.volume_type.name)

    def test_offering_component_name_is_updated(self):
        self.volume_type.name = 'new name'
        self.volume_type.save()
        component = marketplace_models.OfferingComponent.objects.get(
            scope=self.volume_type
        )
        self.assertEqual(component.name, 'Storage (%s)' % self.volume_type.name)

    def test_offering_component_is_deleted(self):
        self.volume_type.delete()
        self.assertRaises(
            marketplace_models.OfferingComponent.DoesNotExist,
            marketplace_models.OfferingComponent.objects.get,
            scope=self.volume_type,
        )

    def test_switch_from_fixed_to_dynamic_billing(self):
        self.offering.plugin_options = {'storage_mode': STORAGE_MODE_FIXED}
        url = marketplace_factories.OfferingFactory.get_url(self.offering)
        new_options = {
            'plugin_options': {'storage_mode': STORAGE_MODE_DYNAMIC},
            'plans': [
                {
                    'name': 'small',
                    'description': 'CPU 1',
                    'prices': {'gigabytes_' + self.volume_type.name: 10},
                }
            ],
        }

        self.client.force_authenticate(self.fixture.staff)
        response = self.client.patch(url, new_options)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.offering.refresh_from_db()
        self.assertEqual(
            self.offering.plugin_options['storage_mode'], STORAGE_MODE_DYNAMIC
        )

    def test_switch_from_dynamic_to_fixed_billing(self):
        self.offering.plugin_options = {'storage_mode': STORAGE_MODE_DYNAMIC}
        url = marketplace_factories.OfferingFactory.get_url(self.offering)
        new_options = {'plugin_options': {'storage_mode': STORAGE_MODE_FIXED}}

        self.client.force_authenticate(self.fixture.staff)
        response = self.client.patch(url, new_options)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.offering.refresh_from_db()
        self.assertEqual(
            self.offering.plugin_options['storage_mode'], STORAGE_MODE_FIXED
        )
