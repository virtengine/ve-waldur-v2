from __future__ import unicode_literals

import mock
from ddt import data, ddt
from rest_framework import status, test

from waldur_core.structure.models import CustomerRole
from waldur_core.structure.tests import fixtures, factories as structure_factories
from waldur_mastermind.marketplace.base import override_marketplace_settings
from waldur_mastermind.marketplace.tests.factories import OFFERING_OPTIONS

from . import factories
from .. import models


@ddt
class OrderGetTest(test.APITransactionTestCase):

    def setUp(self):
        self.fixture = fixtures.ProjectFixture()
        self.project = self.fixture.project
        self.manager = self.fixture.manager
        self.order = factories.OrderFactory(project=self.project, created_by=self.manager)

    @data('staff', 'owner', 'admin', 'manager')
    def test_orders_should_be_visible_to_colleagues_and_staff(self, user):
        user = getattr(self.fixture, user)
        self.client.force_authenticate(user)
        url = factories.OrderFactory.get_list_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    @data('user')
    def test_orders_should_be_invisible_to_other_users(self, user):
        user = getattr(self.fixture, user)
        self.client.force_authenticate(user)
        url = factories.OrderFactory.get_list_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)

    def test_items_should_be_invisible_to_unauthenticated_users(self):
        url = factories.OrderFactory.get_list_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@ddt
class OrderCreateTest(test.APITransactionTestCase):

    def setUp(self):
        self.fixture = fixtures.ProjectFixture()
        self.project = self.fixture.project

    @data('staff', 'owner', 'admin', 'manager')
    def test_user_can_create_order_in_valid_project(self, user):
        user = getattr(self.fixture, user)
        response = self.create_order(user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(models.Order.objects.filter(created_by=user).exists())
        self.assertEqual(1, len(response.data['items']))

    @data('user')
    def test_user_can_not_create_order_in_invalid_project(self, user):
        user = getattr(self.fixture, user)
        response = self.create_order(user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_not_create_item_if_offering_is_not_available(self):
        offering = factories.OfferingFactory(state=models.Offering.States.ARCHIVED)
        response = self.create_order(self.fixture.staff, offering)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_with_plan(self):
        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE)
        plan = factories.PlanFactory(offering=offering)
        add_payload = {'items': [
            {
                'offering': factories.OfferingFactory.get_url(offering),
                'plan': factories.PlanFactory.get_url(plan),
                'attributes': {}
            },
        ]}
        response = self.create_order(self.fixture.staff, offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @mock.patch('waldur_mastermind.marketplace.tasks.notify_order_approvers.delay')
    def test_notification_is_sent_when_order_is_created(self, mock_task):
        offering = factories.OfferingFactory(
            state=models.Offering.States.ACTIVE, shared=True, billable=True)
        plan = factories.PlanFactory(offering=offering)
        add_payload = {'items': [
            {
                'offering': factories.OfferingFactory.get_url(offering),
                'plan': factories.PlanFactory.get_url(plan),
                'attributes': {}
            },
        ]}
        response = self.create_order(self.fixture.manager, offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_task.assert_called_once()

    def test_can_not_create_order_if_offering_is_not_available_to_customer(self):
        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE, shared=False)
        offering.customer.add_user(self.fixture.owner, CustomerRole.OWNER)
        plan = factories.PlanFactory(offering=offering)
        add_payload = {'items': [
            {
                'offering': factories.OfferingFactory.get_url(offering),
                'plan': factories.PlanFactory.get_url(plan),
                'attributes': {}
            },
        ]}
        response = self.create_order(self.fixture.owner, offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_not_create_order_with_plan_related_to_another_offering(self):
        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE)
        plan = factories.PlanFactory(offering=offering)
        add_payload = {'items': [
            {
                'offering': factories.OfferingFactory.get_url(),
                'plan': factories.PlanFactory.get_url(plan),
                'attributes': {}
            },
        ]}
        response = self.create_order(self.fixture.staff, offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_not_create_order_if_plan_max_amount_has_been_reached(self):
        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE)
        plan = factories.PlanFactory(offering=offering, max_amount=3)
        factories.ResourceFactory.create_batch(3, plan=plan, offering=offering)
        add_payload = {'items': [
            {
                'offering': factories.OfferingFactory.get_url(offering),
                'plan': factories.PlanFactory.get_url(plan),
                'attributes': {}
            },
        ]}
        response = self.create_order(self.fixture.staff, offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_create_order_with_valid_attributes_specified_by_options(self):
        attributes = {
            'storage': 1000,
            'ram': 30,
            'cpu_count': 5,
        }
        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE, options=OFFERING_OPTIONS)
        plan = factories.PlanFactory(offering=offering)
        add_payload = {'items': [
            {
                'offering': factories.OfferingFactory.get_url(offering),
                'plan': factories.PlanFactory.get_url(plan),
                'attributes': attributes,
            },
        ]}
        response = self.create_order(self.fixture.staff, offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['items'][0]['attributes'], attributes)

    def test_user_can_not_create_order_with_invalid_attributes(self):
        attributes = {
            'storage': 'invalid value',
        }
        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE, options=OFFERING_OPTIONS)
        plan = factories.PlanFactory(offering=offering)
        add_payload = {'items': [
            {
                'offering': factories.OfferingFactory.get_url(offering),
                'plan': factories.PlanFactory.get_url(plan),
                'attributes': attributes,
            },
        ]}
        response = self.create_order(self.fixture.staff, offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_create_order_with_valid_limits(self):
        limits = {
            'storage': 1000,
            'ram': 30,
            'cpu_count': 5,
        }

        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE)
        plan = factories.PlanFactory(offering=offering)

        for key in limits.keys():
            models.OfferingComponent.objects.create(
                offering=offering,
                type=key,
                billing_type=models.OfferingComponent.BillingTypes.USAGE
            )

        add_payload = {
            'items': [
                {
                    'offering': factories.OfferingFactory.get_url(offering),
                    'plan': factories.PlanFactory.get_url(plan),
                    'limits': limits,
                    'attributes': {},
                },
            ]
        }

        response = self.create_order(self.fixture.staff, offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        order_item = models.OrderItem.objects.last()
        self.assertEqual(order_item.limits['cpu_count'], 5)

    def test_user_can_not_create_order_with_invalid_limits(self):
        limits = {
            'storage': 1000,
            'ram': 30,
            'cpu_count': 5,
        }

        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE)
        plan = factories.PlanFactory(offering=offering)

        for key in limits.keys():
            models.OfferingComponent.objects.create(
                offering=offering,
                type=key,
                billing_type=models.OfferingComponent.BillingTypes.FIXED
            )

        add_payload = {
            'items': [
                {
                    'offering': factories.OfferingFactory.get_url(offering),
                    'plan': factories.PlanFactory.get_url(plan),
                    'limits': limits,
                    'attributes': {},
                },
            ]
        }

        response = self.create_order(self.fixture.staff, offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_creating_is_not_available_for_blocked_organization(self):
        user = self.fixture.owner
        self.fixture.customer.blocked = True
        self.fixture.customer.save()
        response = self.create_order(user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_create_order_if_terms_of_service_have_been_accepted(self):
        user = self.fixture.admin
        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE)
        offering.terms_of_service = 'Terms of service'
        offering.save()
        add_payload = {
            'items': [
                {
                    'offering': factories.OfferingFactory.get_url(offering),
                    'attributes': {},
                    'accepting_terms_of_service': True
                },
            ]
        }
        response = self.create_order(user, offering=offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(models.Order.objects.filter(created_by=user).exists())
        self.assertEqual(1, len(response.data['items']))

    def test_user_can_create_order_if_terms_of_service_are_not_filled(self):
        user = self.fixture.admin
        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE)
        add_payload = {
            'items': [
                {
                    'offering': factories.OfferingFactory.get_url(offering),
                    'attributes': {},
                },
            ]
        }
        response = self.create_order(user, offering=offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(models.Order.objects.filter(created_by=user).exists())
        self.assertEqual(1, len(response.data['items']))

    def test_user_can_create_order_if_offering_is_not_shared(self):
        user = self.fixture.admin
        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE)
        offering.shared = False
        offering.customer = self.project.customer
        offering.save()
        add_payload = {
            'items': [
                {
                    'offering': factories.OfferingFactory.get_url(offering),
                    'attributes': {},
                },
            ]
        }
        response = self.create_order(user, offering=offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(models.Order.objects.filter(created_by=user).exists())
        self.assertEqual(1, len(response.data['items']))

    def test_user_cannot_create_order_if_terms_of_service_have_been_not_accepted(self):
        user = self.fixture.admin
        offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE)
        offering.terms_of_service = 'Terms of service'
        offering.save()
        add_payload = {
            'items': [
                {
                    'offering': factories.OfferingFactory.get_url(offering),
                    'attributes': {}
                },
            ]
        }
        response = self.create_order(user, offering=offering, add_payload=add_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.content,
                         '{"items":["Terms of service for offering \'%s\' have not been accepted."]}' % offering)
        self.assertFalse(models.Order.objects.filter(created_by=user).exists())

    def create_order(self, user, offering=None, add_payload=None):
        if offering is None:
            offering = factories.OfferingFactory(state=models.Offering.States.ACTIVE)
        self.client.force_authenticate(user)
        url = factories.OrderFactory.get_list_url()
        payload = {
            'project': structure_factories.ProjectFactory.get_url(self.project),
            'items': [
                {
                    'offering': factories.OfferingFactory.get_url(offering),
                    'attributes': {}
                },
            ]
        }

        if add_payload:
            payload.update(add_payload)

        return self.client.post(url, payload)


@ddt
class OrderApproveTest(test.APITransactionTestCase):

    def setUp(self):
        self.fixture = fixtures.ProjectFixture()
        self.project = self.fixture.project
        self.manager = self.fixture.manager
        self.order = factories.OrderFactory(project=self.project, created_by=self.manager)
        self.url = factories.OrderFactory.get_url(self.order, 'approve')

    def test_owner_can_approve_order(self):
        self.ensure_user_can_approve_order(self.fixture.owner)

    def test_by_default_manager_can_not_approve_order(self):
        self.ensure_user_can_not_approve_order(self.fixture.manager)

    def test_by_default_admin_can_not_approve_order(self):
        self.ensure_user_can_not_approve_order(self.fixture.admin)

    @override_marketplace_settings(MANAGER_CAN_APPROVE_ORDER=True)
    def test_manager_can_approve_order_if_feature_is_enabled(self):
        self.ensure_user_can_approve_order(self.fixture.manager)

    @override_marketplace_settings(ADMIN_CAN_APPROVE_ORDER=True)
    def test_admin_can_approve_order_if_feature_is_enabled(self):
        self.ensure_user_can_approve_order(self.fixture.admin)

    def test_user_can_not_reapprove_active_order(self):
        self.order.state = models.Order.States.EXECUTING
        self.order.save()
        response = self.approve_order(self.fixture.owner)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.order.approved_by, None)

    def test_order_approving_is_not_available_for_blocked_organization(self):
        self.order.project.customer.blocked = True
        self.order.project.customer.save()
        response = self.approve_order(self.fixture.owner)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def approve_order(self, user):
        self.client.force_authenticate(user)

        response = self.client.post(self.url)
        self.order.refresh_from_db()
        return response

    def ensure_user_can_approve_order(self, user):
        response = self.approve_order(user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.order.approved_by, user)

    def ensure_user_can_not_approve_order(self, user):
        response = self.approve_order(user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.order.approved_by, None)


@ddt
class OrderRejectTest(test.APITransactionTestCase):

    def setUp(self):
        self.fixture = fixtures.ProjectFixture()
        self.project = self.fixture.project
        self.manager = self.fixture.manager
        self.order = factories.OrderFactory(project=self.project, created_by=self.manager)
        self.order_item_1 = factories.OrderItemFactory(order=self.order)
        self.order_item_2 = factories.OrderItemFactory(order=self.order)
        self.url = factories.OrderFactory.get_url(self.order, 'reject')

    @data('staff', 'manager')
    def test_staff_and_order_owner_can_reject_order(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.post(self.url)

        for obj in [self.order, self.order_item_1, self.order_item_2]:
            obj.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.order.state, models.Order.States.REJECTED)
        self.assertEqual(self.order_item_1.state, models.OrderItem.States.TERMINATED)
        self.assertEqual(self.order_item_2.state, models.OrderItem.States.TERMINATED)

    @data('admin', 'owner')
    def test_other_users_can_not_reject_order(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_not_reject_unrequested_order(self):
        self.client.force_authenticate(self.fixture.staff)
        self.order.approve()
        self.order.save()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_order_rejecting_is_not_available_for_blocked_organization(self):
        self.order.project.customer.blocked = True
        self.order.project.customer.save()
        self.client.force_authenticate(self.fixture.manager)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@ddt
class OrderDeleteTest(test.APITransactionTestCase):

    def setUp(self):
        self.fixture = fixtures.ProjectFixture()
        self.project = self.fixture.project
        self.manager = self.fixture.manager
        self.order = factories.OrderFactory(project=self.project, created_by=self.manager)

    @data('staff', 'owner')
    def test_owner_and_staff_can_delete_order(self, user):
        response = self.delete_order(user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertFalse(models.Order.objects.filter(created_by=self.manager).exists())

    @data('admin', 'manager')
    def test_other_colleagues_can_not_delete_order(self, user):
        response = self.delete_order(user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(models.Order.objects.filter(created_by=self.manager).exists())

    @data('user')
    def test_other_user_can_not_delete_order(self, user):
        response = self.delete_order(user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(models.Order.objects.filter(created_by=self.manager).exists())

    def test_order_deleting_is_not_available_for_blocked_organization(self):
        self.fixture.customer.blocked = True
        self.fixture.customer.save()
        response = self.delete_order('owner')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def delete_order(self, user):
        user = getattr(self.fixture, user)
        self.client.force_authenticate(user)
        url = factories.OrderFactory.get_url(self.order)
        response = self.client.delete(url)
        return response


class OrderStateTest(test.APITransactionTestCase):
    def test_switch_order_state_to_done_when_all_order_items_are_processed(self):
        order_item = factories.OrderItemFactory(state=models.OrderItem.States.EXECUTING)
        order = order_item.order
        order.state = models.Order.States.EXECUTING
        order.save()
        order_item.state = models.OrderItem.States.DONE
        order_item.save()
        order.refresh_from_db()
        self.assertEqual(order.state, models.Order.States.DONE)

    def test_not_switch_order_state_to_done_when_not_all_order_items_are_processed(self):
        order_item = factories.OrderItemFactory(state=models.OrderItem.States.EXECUTING)
        order = order_item.order
        factories.OrderItemFactory(state=models.OrderItem.States.EXECUTING, order=order)
        order.state = models.Order.States.EXECUTING
        order.save()
        order_item.state = models.OrderItem.States.DONE
        order_item.save()
        order.refresh_from_db()
        self.assertEqual(order.state, models.Order.States.EXECUTING)
