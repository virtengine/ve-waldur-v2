from rest_framework import test

from .. import fixtures


class TenantQuotasTest(test.APITransactionTestCase):

    def setUp(self):
        super(TenantQuotasTest, self).setUp()
        self.fixture = fixtures.OpenStackTenantFixture()
        self.tenant = self.fixture.tenant

    def test_tenant_quotas_are_synced_with_private_settings_quota(self):
        self.tenant.set_quota_usage('vcpu', 1)
        self.tenant.set_quota_usage('ram', 1024)
        self.tenant.set_quota_usage('storage', 102400)
        self.tenant.set_quota_usage('floating_ip_count', 2)
        self.tenant.set_quota_usage('instances', 1)

        self.assertEqual(self.tenant.quotas.get(name='vcpu').usage, 1)
        self.assertEqual(self.tenant.quotas.get(name='ram').usage, 1024)
        self.assertEqual(self.tenant.quotas.get(name='storage').usage, 102400)
        self.assertEqual(self.tenant.quotas.get(name='floating_ip_count').usage, 2)
        self.assertEqual(self.tenant.quotas.get(name='instances').usage, 1)
