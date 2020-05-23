import itertools
from collections import namedtuple
from unittest.mock import patch

from ddt import data, ddt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status, test

from waldur_core.core.tests.helpers import override_waldur_core_settings
from waldur_core.structure.models import PrivateServiceSettings, ServiceSettings
from waldur_core.structure.tests import factories as structure_factories
from waldur_openstack.openstack.models import Tenant
from waldur_openstack.openstack.tests.helpers import override_openstack_settings
from waldur_openstack.openstack.tests.unittests.test_backend import BaseBackendTestCase

from .. import executors, models
from . import factories, fixtures


@override_openstack_settings(TENANT_CREDENTIALS_VISIBLE=True)
class BaseTenantActionsTest(test.APITransactionTestCase):
    def setUp(self):
        super(BaseTenantActionsTest, self).setUp()
        self.fixture = fixtures.OpenStackFixture()
        self.tenant = self.fixture.tenant
        self.spl = self.fixture.openstack_spl


class TenantGetTest(BaseTenantActionsTest):
    def setUp(self):
        super(TenantGetTest, self).setUp()
        self.fixture.openstack_service_settings.backend_url = 'https://waldur.com/'
        self.fixture.openstack_service_settings.save()

    @override_openstack_settings(TENANT_CREDENTIALS_VISIBLE=False)
    def test_user_name_and_password_and_access_url_are_not_returned_if_credentials_are_not_visible(
        self,
    ):
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.get(factories.TenantFactory.get_url(self.fixture.tenant))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('user_username', response.data)
        self.assertNotIn('user_password', response.data)
        self.assertNotIn('access_url', response.data)

    def test_user_name_and_password_and_access_url_are_returned_if_credentials_are_visible(
        self,
    ):
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.get(factories.TenantFactory.get_url(self.fixture.tenant))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.fixture.tenant.user_username, response.data['user_username']
        )
        self.assertEqual(
            self.fixture.tenant.user_password, response.data['user_password']
        )
        self.assertEqual(
            self.fixture.tenant.get_access_url(), response.data['access_url']
        )


@ddt
class TenantCreateTest(BaseTenantActionsTest):
    def setUp(self):
        super(TenantCreateTest, self).setUp()
        self.valid_data = {
            'name': 'Test tenant',
            'service_project_link': factories.OpenStackServiceProjectLinkFactory.get_url(
                self.fixture.openstack_spl
            ),
        }
        self.url = factories.TenantFactory.get_list_url()
        self.fixture.openstack_service_settings.backend_url = 'https://waldur.com/'
        self.fixture.openstack_service_settings.save()

    @data('admin', 'manager', 'staff', 'owner')
    def test_authorized_user_can_create_tenant(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.post(self.url, data=self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            models.Tenant.objects.filter(name=self.valid_data['name']).exists()
        )

    @data('admin', 'manager', 'owner')
    def test_cannot_create_tenant_with_shared_service_settings(self, user):
        self.fixture.openstack_service_settings.shared = True
        self.fixture.openstack_service_settings.save()
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.post(self.url, data=self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            models.Tenant.objects.filter(name=self.valid_data['name']).exists()
        )

    @data('global_support', 'user')
    def test_unathorized_user_cannot_create_tenant(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.post(self.url, data=self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            models.Tenant.objects.filter(name=self.valid_data['name']).exists()
        )

    @override_waldur_core_settings(ONLY_STAFF_MANAGES_SERVICES=True)
    @data('staff')
    def test_if_only_staff_manages_services_he_can_create_tenant(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.post(self.url, data=self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_waldur_core_settings(ONLY_STAFF_MANAGES_SERVICES=True)
    @data('admin', 'manager', 'owner')
    def test_if_only_staff_manages_services_other_users_can_not_create_tenant(
        self, user
    ):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.post(self.url, data=self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_create_tenant_with_service_settings_username(self):
        self.fixture.openstack_service_settings.username = 'admin'
        self.fixture.openstack_service_settings.save()
        self.assert_can_not_create_tenant(
            'user_username',
            {'user_username': self.fixture.openstack_service_settings.username},
        )

    def test_cannot_create_tenant_with_blacklisted_username(self):
        self.fixture.openstack_service_settings.options['blacklisted_usernames'] = [
            'admin'
        ]
        self.assert_can_not_create_tenant('user_username', {'user_username': 'admin'})

    def test_cannot_create_tenant_with_duplicated_username(self):
        self.fixture.tenant.user_username = 'username'
        self.fixture.tenant.save()

        self.assert_can_not_create_tenant(
            'user_username', {'user_username': self.fixture.tenant.user_username}
        )

    def test_cannot_create_tenant_with_duplicated_tenant_name_in_same_spl(self):
        service_project_link = factories.OpenStackServiceProjectLinkFactory.get_url(
            self.fixture.openstack_spl
        )
        self.assert_can_not_create_tenant(
            'name',
            {
                'name': self.fixture.tenant.name,
                'service_project_link': service_project_link,
            },
        )

    empty_domains = list(
        itertools.combinations_with_replacement((None, '', 'default'), 2)
    )

    @data(('same', 'same'), *empty_domains)
    def test_can_not_create_tenant_with_same_tenant_name_in_other_service_with_same_or_empty_domain(
        self, pair
    ):
        (domain1, domain2) = pair
        self.fixture.openstack_service_settings.domain = domain1
        self.fixture.openstack_service_settings.save()

        other_fixture = fixtures.OpenStackFixture()
        service_settings = other_fixture.openstack_service_settings
        service_settings.backend_url = (
            self.fixture.openstack_service_settings.backend_url
        )
        service_settings.domain = domain2
        service_settings.save()

        service_project_link = factories.OpenStackServiceProjectLinkFactory.get_url(
            other_fixture.openstack_spl
        )
        self.assert_can_not_create_tenant(
            'name',
            {
                'name': self.fixture.tenant.name,
                'service_project_link': service_project_link,
            },
        )

    def test_can_create_tenant_with_same_tenant_name_in_other_service_with_same_url_but_other_domain(
        self,
    ):
        self.fixture.openstack_service_settings.domain = 'first'
        self.fixture.openstack_service_settings.save()

        other_fixture = fixtures.OpenStackFixture()
        service_settings = other_fixture.openstack_service_settings
        service_settings.backend_url = (
            self.fixture.openstack_service_settings.backend_url
        )
        service_settings.domain = 'second'
        service_settings.save()

        service_project_link = factories.OpenStackServiceProjectLinkFactory.get_url(
            other_fixture.openstack_spl
        )
        self.assert_can_create_tenant(
            {
                'name': self.fixture.tenant.name,
                'service_project_link': service_project_link,
            }
        )

    def assert_can_create_tenant(self, payload):
        response = self.create_tenant(payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def assert_can_not_create_tenant(self, error_field, payload):
        response = self.create_tenant(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(error_field in response.data)

    def create_tenant(self, payload):
        payload.setdefault('name', 'Test tenant')
        payload.setdefault(
            'service_project_link',
            factories.OpenStackServiceProjectLinkFactory.get_url(
                self.fixture.openstack_spl
            ),
        )
        self.client.force_authenticate(self.fixture.staff)
        return self.client.post(self.url, data=payload)

    @override_openstack_settings(TENANT_CREDENTIALS_VISIBLE=False)
    def test_user_name_and_password_are_autogenerated_if_credentials_are_not_visible(
        self,
    ):
        self.client.force_authenticate(self.fixture.staff)
        payload = self.valid_data.copy()
        payload['user_username'] = 'random'
        payload['user_password'] = '12345678secret'

        response = self.client.post(self.url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tenant = models.Tenant.objects.get(name=payload['name'])
        self.assertIsNotNone(tenant.user_username)
        self.assertIsNotNone(tenant.user_password)
        self.assertNotEqual(tenant.user_username, payload['user_username'])
        self.assertNotEqual(tenant.user_password, payload['user_password'])

    def test_user_can_set_username_if_autogeneration_is_disabled(self):
        self.client.force_authenticate(self.fixture.staff)
        payload = self.valid_data.copy()
        payload['user_username'] = 'random'

        response = self.client.post(self.url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tenant = models.Tenant.objects.get(name=payload['name'])
        self.assertIsNotNone(tenant.user_username)
        self.assertIsNotNone(tenant.user_password)
        self.assertEqual(tenant.user_username, payload['user_username'])

    @override_openstack_settings(
        DEFAULT_SECURITY_GROUPS=(
            {
                'name': 'allow-all',
                'description': 'Security group for any access',
                'rules': (
                    {
                        'protocol': 'icmp',
                        'cidr': '0.0.0.0/0',
                        'icmp_type': -1,
                        'icmp_code': -1,
                    },
                    {
                        'protocol': 'tcp',
                        'cidr': '0.0.0.0/0',
                        'from_port': 1,
                        'to_port': 65535,
                    },
                ),
            },
            {
                'name': 'ssh',
                'description': 'Security group for secure shell access',
                'rules': (
                    {
                        'protocol': 'tcp',
                        'cidr': '0.0.0.0/0',
                        'from_port': 22,
                        'to_port': 22,
                    },
                ),
            },
        )
    )
    def test_default_security_groups_are_created(self):
        expected_security_groups = settings.WALDUR_OPENSTACK['DEFAULT_SECURITY_GROUPS']
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.post(self.url, data=self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tenant = models.Tenant.objects.get(name=self.valid_data['name'])
        self.assertEqual(len(expected_security_groups), tenant.security_groups.count())
        allow_all = expected_security_groups[0]
        tenant_sg = tenant.security_groups.get(name='allow-all')
        expected_icmp_rule = [
            rule for rule in allow_all['rules'] if rule['protocol'] == 'icmp'
        ][0]
        icmp_rule = tenant_sg.rules.get(protocol='icmp')
        self.assertEqual(expected_icmp_rule['icmp_type'], icmp_rule.from_port)
        self.assertEqual(expected_icmp_rule['icmp_code'], icmp_rule.to_port)

    @override_openstack_settings(
        DEFAULT_SECURITY_GROUPS=(
            {
                'description': 'Security group for any access',
                'rules': (
                    {
                        'protocol': 'icmp',
                        'cidr': '0.0.0.0/0',
                        'icmp_type': -1,
                        'icmp_code': -1,
                    },
                    {
                        'protocol': 'tcp',
                        'cidr': '0.0.0.0/0',
                        'from_port': 1,
                        'to_port': 65535,
                    },
                ),
            },
        )
    )
    def test_tenant_is_not_created_if_configured_security_groups_have_no_name(self):
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.post(self.url, data=self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_openstack_settings(
        DEFAULT_SECURITY_GROUPS=(
            {'name': 'allow-all', 'description': 'Security group for any access',},
        )
    )
    def test_tenant_is_not_created_if_configured_security_groups_rules_are_not_present(
        self,
    ):
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.post(self.url, data=self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('waldur_openstack.openstack.executors.core_tasks.BackendMethodTask')
    def test_override_external_network_id_if_exists_customer_openstack(
        self, mock_core_tasks
    ):
        EXTERNAL_NETWORK_ID = 'test_external_network_id'
        self.client.force_authenticate(self.fixture.staff)
        self.fixture.openstack_spl.service.settings.shared = True
        factories.CustomerOpenStackFactory(
            settings=self.fixture.openstack_spl.service.settings,
            customer=self.fixture.openstack_spl.project.customer,
            external_network_id=EXTERNAL_NETWORK_ID,
        )
        self.client.post(self.url, data=self.valid_data)
        mock_kwargs = [
            s[2]
            for s in mock_core_tasks.mock_calls
            if 'connect_tenant_to_external_network' in s[1]
        ]
        self.assertEqual(EXTERNAL_NETWORK_ID, mock_kwargs[0]['external_network_id'])


@ddt
class TenantUpdateTest(BaseTenantActionsTest):
    def test_user_cannot_update_username_even_if_credentials_autogeneration_is_disabled(
        self,
    ):
        self.client.force_authenticate(self.fixture.staff)
        payload = dict(name=self.fixture.tenant.name, user_username='new_username')

        response = self.client.put(self.get_url(), payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotEqual(response.data['user_username'], payload['user_username'])

    def test_cannot_update_tenant_with_duplicated_tenant_name(self):
        other_tenant = factories.TenantFactory(
            service_project_link=self.fixture.openstack_spl
        )
        payload = dict(name=other_tenant.name)

        self.client.force_authenticate(self.fixture.staff)
        response = self.client.put(self.get_url(), payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(models.Tenant.objects.filter(name=payload['name']).count(), 1)

    @override_waldur_core_settings(ONLY_STAFF_MANAGES_SERVICES=True)
    @data('staff')
    def test_if_only_staff_manages_services_he_can_update_tenant(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.patch(self.get_url(), dict(name='new valid tenant name'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_waldur_core_settings(ONLY_STAFF_MANAGES_SERVICES=True)
    @data('admin', 'manager', 'owner')
    def test_if_only_staff_manages_services_other_users_can_not_update_tenant(
        self, user
    ):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.patch(self.get_url(), dict(name='new valid tenant name'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('waldur_openstack.openstack.executors.core_tasks.BackendMethodTask')
    def test_update_service_setting_options_if_updated_scope(self, mock_core_tasks):
        tenant_service_setting = PrivateServiceSettings.objects.get(
            scope=self.fixture.tenant
        )
        NEW_EXTERNAL_NETWORK_ID = 'new_external_network_id'
        self.fixture.tenant.external_network_id = NEW_EXTERNAL_NETWORK_ID
        self.fixture.tenant.save()
        tenant_service_setting.refresh_from_db()
        self.assertEqual(
            tenant_service_setting.get_option('external_network_id'),
            NEW_EXTERNAL_NETWORK_ID,
        )

    def test_updating_openstack_tenant_name_should_lead_to_update_of_a_provider_name(
        self,
    ):
        self.service_settings = factories.OpenStackServiceSettingsFactory()
        self.service_settings.scope = self.tenant
        self.service_settings.save()

        self.client.force_authenticate(self.fixture.staff)
        new_name = 'New name'
        self.client.put(self.get_url(), {'name': new_name})
        self.service_settings.refresh_from_db()
        self.assertEqual(self.service_settings.name, new_name)

    def get_url(self):
        return factories.TenantFactory.get_url(self.fixture.tenant)


@patch('waldur_openstack.openstack.executors.TenantPushQuotasExecutor.execute')
class TenantQuotasTest(BaseTenantActionsTest):
    def test_non_staff_user_cannot_set_tenant_quotas(self, mocked_task):
        self.client.force_authenticate(user=structure_factories.UserFactory())
        response = self.client.post(self.get_url())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(mocked_task.called)

    def test_staff_can_set_tenant_quotas(self, mocked_task):
        self.client.force_authenticate(self.fixture.staff)
        quotas_data = {'security_group_count': 100, 'security_group_rule_count': 100}
        response = self.client.post(self.get_url(), data=quotas_data)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mocked_task.assert_called_once_with(self.tenant, quotas=quotas_data)

    def get_url(self):
        return factories.TenantFactory.get_url(self.tenant, 'set_quotas')


@patch('waldur_openstack.openstack.executors.TenantPullExecutor.execute')
class TenantPullTest(BaseTenantActionsTest):
    def test_staff_can_pull_tenant(self, mocked_task):
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.post(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mocked_task.assert_called_once_with(self.tenant)

    def test_it_should_not_be_possible_to_pull_tenant_without_backend_id(
        self, mocked_task
    ):
        # Arrange
        self.tenant.backend_id = ''
        self.tenant.save()

        # Act
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.post(self.get_url())

        # Assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(0, mocked_task.call_count)

    def get_url(self):
        return factories.TenantFactory.get_url(self.tenant, 'pull')


@patch('waldur_openstack.openstack.executors.TenantPullQuotasExecutor.execute')
class TenantPullQuotasTest(BaseTenantActionsTest):
    def test_staff_can_pull_tenant_quotas(self, mocked_task):
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.post(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mocked_task.assert_called_once_with(self.tenant)

    def get_url(self):
        return factories.TenantFactory.get_url(self.tenant, 'pull_quotas')


@ddt
@patch('waldur_openstack.openstack.executors.TenantDeleteExecutor.execute')
class TenantDeleteTest(BaseTenantActionsTest):
    @data('staff', 'owner', 'admin', 'manager')
    def test_can_delete_tenant(self, user, mocked_task):
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.delete(self.get_url())

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mocked_task.assert_called_once_with(self.tenant, is_async=True, force=False)

    @data('admin', 'manager')
    def test_cannot_delete_tenant_from_shared_settings(self, user, mocked_task):
        self.fixture.openstack_service_settings.shared = True
        self.fixture.openstack_service_settings.save()
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.delete(self.get_url())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(mocked_task.call_count, 0)

    @override_openstack_settings(MANAGER_CAN_MANAGE_TENANTS=True)
    def test_manager_can_delete_tenant_from_shared_settings_with_permission_from_settings(
        self, mocked_task
    ):
        # Arrange
        self.fixture.openstack_service_settings.shared = True
        self.fixture.openstack_service_settings.save()

        # Act
        self.client.force_authenticate(user=self.fixture.manager)
        response = self.client.delete(self.get_url())

        # Assert
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mocked_task.assert_called_once_with(self.tenant, is_async=True, force=False)

    @override_openstack_settings(ADMIN_CAN_MANAGE_TENANTS=True)
    def test_admin_can_delete_tenant_from_shared_settings_with_permission_from_settings(
        self, mocked_task
    ):
        # Arrange
        self.fixture.openstack_service_settings.shared = True
        self.fixture.openstack_service_settings.save()

        # Act
        self.client.force_authenticate(user=self.fixture.admin)
        response = self.client.delete(self.get_url())

        # Assert
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mocked_task.assert_called_once_with(self.tenant, is_async=True, force=False)

    @data('global_support')
    def test_cannot_delete_tenant(self, user, mocked_task):
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.delete(self.get_url())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(mocked_task.call_count, 0)

    @override_waldur_core_settings(ONLY_STAFF_MANAGES_SERVICES=True)
    @data('staff')
    def test_if_only_staff_manages_services_he_can_delete_tenant(
        self, user, mocked_task
    ):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.delete(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(mocked_task.call_count, 1)

    @override_waldur_core_settings(ONLY_STAFF_MANAGES_SERVICES=True)
    @data('admin', 'manager', 'owner')
    def test_if_only_staff_manages_services_other_users_can_not_delete_tenant(
        self, user, mocked_task
    ):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.delete(self.get_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(mocked_task.call_count, 0)

    def get_url(self):
        return factories.TenantFactory.get_url(self.tenant)


class TenantActionsMetadataTest(BaseTenantActionsTest):
    def test_if_tenant_is_ok_actions_enabled(self):
        self.client.force_authenticate(self.fixture.staff)
        actions = self.get_actions()
        self.assertTrue(actions['set_quotas']['enabled'])

    def test_if_tenant_is_not_ok_actions_disabled(self):
        self.tenant.state = Tenant.States.DELETING
        self.tenant.save()

        self.client.force_authenticate(self.fixture.owner)
        actions = self.get_actions()
        self.assertFalse(actions['set_quotas']['enabled'])

    def get_actions(self):
        url = factories.TenantFactory.get_url(self.tenant)
        response = self.client.options(url)
        return response.data['actions']


@patch('waldur_openstack.openstack.executors.FloatingIPCreateExecutor.execute')
class TenantCreateFloatingIPTest(BaseTenantActionsTest):
    def setUp(self):
        super(TenantCreateFloatingIPTest, self).setUp()
        self.client.force_authenticate(self.fixture.owner)
        self.url = factories.TenantFactory.get_url(self.tenant, 'create_floating_ip')

    def test_that_floating_ip_count_quota_increases_when_floating_ip_is_created(
        self, mocked_task
    ):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.tenant.floating_ips.count(), 1)
        self.assertTrue(mocked_task.called)

    def test_that_floating_ip_count_quota_exceeds_limit_if_too_many_ips_are_created(
        self, mocked_task
    ):
        self.tenant.set_quota_limit('floating_ip_count', 0)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.tenant.floating_ips.count(), 0)
        self.assertFalse(mocked_task.called)

    def test_user_cannot_create_floating_ip_if_external_network_is_not_defined_for_tenant(
        self, mocked_task
    ):
        self.tenant.external_network_id = ''
        self.tenant.save()

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.tenant.floating_ips.count(), 0)
        self.assertFalse(mocked_task.called)


@patch('waldur_openstack.openstack.executors.NetworkCreateExecutor.execute')
class TenantCreateNetworkTest(BaseTenantActionsTest):
    quota_name = 'network_count'

    def setUp(self):
        super(TenantCreateNetworkTest, self).setUp()
        self.client.force_authenticate(self.fixture.owner)
        self.url = factories.TenantFactory.get_url(self.tenant, 'create_network')
        self.request_data = {'name': 'test_network_name'}

    def test_that_network_quota_is_increased_when_network_is_created(self, mocked_task):
        response = self.client.post(self.url, self.request_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.tenant.networks.count(), 1)
        self.assertEqual(self.tenant.quotas.get(name=self.quota_name).usage, 1)
        self.assertTrue(mocked_task.called)

    def test_that_network_is_not_created_when_quota_exceeds_set_limit(
        self, mocked_task
    ):
        self.tenant.set_quota_limit(self.quota_name, 0)
        response = self.client.post(self.url, self.request_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.tenant.networks.count(), 0)
        self.assertEqual(self.tenant.quotas.get(name=self.quota_name).usage, 0)
        self.assertFalse(mocked_task.called)


@ddt
class TenantChangePasswordTest(BaseTenantActionsTest):
    def setUp(self):
        super(TenantChangePasswordTest, self).setUp()
        self.tenant = self.fixture.tenant
        self.url = factories.TenantFactory.get_url(
            self.tenant, action='change_password'
        )
        self.new_password = get_user_model().objects.make_random_password()[:50]

    @data('owner', 'staff', 'admin', 'manager')
    def test_user_can_change_tenant_user_password(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.post(self.url, {'user_password': self.new_password})

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.user_password, self.new_password)

    @data('global_support', 'customer_support', 'project_support')
    def test_user_cannot_change_tenant_user_password(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.post(self.url, {'user_password': self.new_password})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cannot_set_password_if_it_consists_only_with_digits(self):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.post(self.url, {'user_password': 682992000})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_set_password_with_length_less_than_8_characters(self):
        request_data = {
            'user_password': get_user_model().objects.make_random_password()[:7]
        }

        self.client.force_authenticate(self.fixture.owner)
        response = self.client.post(self.url, request_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_set_password_if_it_matches_to_the_old_one(self):
        self.client.force_authenticate(self.fixture.owner)

        response = self.client.post(
            self.url, {'user_password': self.fixture.tenant.user_password}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_change_password_if_tenant_is_not_in_OK_state(self):
        self.tenant.state = self.tenant.States.ERRED
        self.tenant.save()

        self.client.force_authenticate(self.fixture.owner)
        response = self.client.post(
            self.url, {'user_password': self.fixture.tenant.user_password}
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_user_can_set_an_empty_password(self):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.post(self.url, {'user_password': ''})

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)


@ddt
class SecurityGroupCreateTest(BaseTenantActionsTest):
    def setUp(self):
        super(SecurityGroupCreateTest, self).setUp()
        self.valid_data = {
            'name': 'test_security_group',
            'description': 'test security_group description',
            'rules': [
                {
                    'protocol': 'tcp',
                    'from_port': 1,
                    'to_port': 10,
                    'cidr': '11.11.1.2/24',
                }
            ],
        }
        self.url = factories.TenantFactory.get_url(
            self.fixture.tenant, action='create_security_group'
        )

    @data('owner', 'admin', 'manager')
    def test_user_with_access_can_create_security_group(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            models.SecurityGroup.objects.filter(name=self.valid_data['name']).exists()
        )

    def test_security_group_can_not_be_created_if_quota_is_over_limit(self):
        self.fixture.tenant.set_quota_limit('security_group_count', 0)

        self.client.force_authenticate(self.fixture.admin)
        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            models.SecurityGroup.objects.filter(name=self.valid_data['name']).exists()
        )

    def test_security_group_quota_increases_on_security_group_creation(self):
        self.client.force_authenticate(self.fixture.admin)
        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.fixture.tenant.quotas.get(name='security_group_count').usage, 1
        )
        self.assertEqual(
            self.fixture.tenant.quotas.get(name='security_group_rule_count').usage, 1
        )

    def test_security_group_can_not_be_created_if_rules_quota_is_over_limit(self):
        self.fixture.tenant.set_quota_limit('security_group_rule_count', 0)

        self.client.force_authenticate(self.fixture.admin)
        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            models.SecurityGroup.objects.filter(name=self.valid_data['name']).exists()
        )

    def test_security_group_creation_starts_sync_task(self):
        self.client.force_authenticate(self.fixture.admin)

        with patch(
            'waldur_openstack.openstack.executors.SecurityGroupCreateExecutor.execute'
        ) as mocked_execute:
            response = self.client.post(self.url, data=self.valid_data)

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.data
            )
            security_group = models.SecurityGroup.objects.get(
                name=self.valid_data['name']
            )

            mocked_execute.assert_called_once_with(security_group)

    def test_security_group_raises_validation_error_if_rule_port_is_invalid(self):
        self.valid_data['rules'][0]['to_port'] = 80000

        self.client.force_authenticate(self.fixture.admin)
        response = self.client.post(self.url, data=self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            models.SecurityGroup.objects.filter(name=self.valid_data['name']).exists()
        )


@ddt
class TenantImportableResourcesTest(BaseTenantActionsTest):
    @patch('waldur_openstack.openstack.backend.OpenStackBackend.get_tenants_for_import')
    def test_user_can_list_importable_resources(self, get_tenants_for_import_mock):
        self.client.force_authenticate(self.fixture.staff)
        backend_tenants = [factories.TenantFactory.build(service_project_link=self.spl)]
        get_tenants_for_import_mock.return_value = backend_tenants
        url = factories.TenantFactory.get_list_url('importable_resources')
        payload = {
            'service_project_link': factories.OpenStackServiceProjectLinkFactory.get_url(
                self.spl
            )
        }

        response = self.client.get(url, payload)

        self.assertEquals(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEquals(len(response.data), len(backend_tenants))
        returned_backend_ids = [item['backend_id'] for item in response.data]
        expected_backend_ids = [item.backend_id for item in backend_tenants]
        self.assertEqual(sorted(returned_backend_ids), sorted(expected_backend_ids))
        get_tenants_for_import_mock.assert_called()

    @data('admin', 'manager', 'owner')
    def test_user_does_not_have_permissions_to_list_resources(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        url = factories.TenantFactory.get_list_url('importable_resources')
        payload = {
            'service_project_link': factories.OpenStackServiceProjectLinkFactory.get_url(
                self.spl
            )
        }

        response = self.client.get(url, payload)

        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)


@ddt
class TenantImportTest(BaseBackendTestCase):
    def setUp(self):
        super(TenantImportTest, self).setUp()
        self.fixture = fixtures.OpenStackFixture()
        self.backend_tenant = factories.TenantFactory.build(
            service_project_link=self.fixture.openstack_spl
        )

    def test_tenant_is_imported(self):
        response = self.import_tenant()

        self.assertEquals(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEquals(response.data['backend_id'], self.backend_tenant.backend_id)
        self.assertTrue(
            models.Tenant.objects.filter(
                backend_id=self.backend_tenant.backend_id
            ).exists()
        )

    @patch('waldur_core.structure.handlers.event_logger')
    def test_event_is_emitted(self, logger_mock):
        self.import_tenant()

        actual = logger_mock.resource.info.call_args[0][0]
        expected = 'Resource {resource_full_name} has been imported.'
        self.assertEqual(expected, actual)

    @data('admin', 'manager', 'owner')
    def test_user_cannot_import_tenant(self, user):
        response = self.import_tenant(user)
        self.assertEquals(
            response.status_code, status.HTTP_403_FORBIDDEN, response.data
        )

    def test_tenant_cannot_be_imported_if_backend_id_exists_already(self):
        self.backend_tenant.save()
        response = self.import_tenant()
        self.assertEquals(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

    def test_imported_tenant_has_user_password_and_username(self):
        response = self.import_tenant()

        self.assertEquals(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEquals(response.data['backend_id'], self.backend_tenant.backend_id)

        self.assertIsNotNone(response.data['user_username'])
        self.assertIsNotNone(response.data['user_password'])

    def test_imported_tenant_settings_have_username_and_password_set(self):
        response = self.import_tenant()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED, response.data)

        tenant = models.Tenant.objects.get(backend_id=self.backend_tenant.backend_id)
        service_settings = ServiceSettings.objects.get(scope=tenant)

        self.assertEquals(tenant.user_username, service_settings.username)
        self.assertEquals(tenant.user_password, service_settings.password)

    def import_tenant(self, user='staff'):
        self.client.force_authenticate(getattr(self.fixture, user))
        payload = {
            'backend_id': self.backend_tenant.backend_id,
            'service_project_link': factories.OpenStackServiceProjectLinkFactory.get_url(
                self.fixture.openstack_spl
            ),
        }
        url = factories.TenantFactory.get_list_url('import_resource')
        FakeProject = namedtuple('Project', 'name description')
        self.mocked_keystone.return_value.projects.get.return_value = FakeProject(
            'admin', 'default'
        )
        return self.client.post(url, payload)


@ddt
class TenantExecutorTest(test.APITransactionTestCase):
    def setUp(self):
        self.fixture = fixtures.OpenStackFixture()
        self.tenant = self.fixture.tenant
        self.network = self.fixture.network
        self.subnet = self.fixture.subnet
        self.subnet.network = self.network
        self.subnet.save()

        self.service_settings = self.fixture.openstack_service_settings
        self.service_settings.options = {'external_network_id': 'external_network_id'}
        self.service_settings.save()

    def test_if_skip_connection_extnet_is_true_task_does_not_exists(self):
        chain = executors.TenantCreateExecutor.get_task_signature(
            self.tenant, 'openstack.tenant:1', skip_connection_extnet=True
        )
        self.assertEqual(
            len(
                [
                    t.args
                    for t in chain.tasks
                    if 'connect_tenant_to_external_network' in t.args
                ]
            ),
            0,
        )

    def test_if_skip_connection_extnet_is_false_task_exists(self):
        chain = executors.TenantCreateExecutor.get_task_signature(
            self.tenant, 'openstack.tenant:1', skip_connection_extnet=False
        )
        self.assertEqual(
            len(
                [
                    t.args
                    for t in chain.tasks
                    if 'connect_tenant_to_external_network' in t.args
                ]
            ),
            1,
        )
