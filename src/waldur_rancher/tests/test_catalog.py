from unittest import mock

from rest_framework import status, test

from . import factories, fixtures, utils


class CatalogCreateTest(test.APITransactionTestCase):
    def setUp(self):
        super().setUp()
        self.fixture = fixtures.RancherFixture()
        self.url = factories.CatalogFactory.get_list_url()

    @utils.override_plugin_settings(READ_ONLY_MODE=True)
    def test_create_is_disabled_in_read_only_mode(self):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch('waldur_rancher.backend.RancherBackend.client')
    def test_create_is_enabled_for_owner(self, mock_backend):
        mock_backend.create_cluster_catalog.return_value = {'id': '1', 'state': 'ok'}
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.post(
            self.url,
            {
                'name': 'Test Catalog',
                'catalog_url': 'http://example.com/',
                'branch': 'master',
                'scope': factories.ClusterFactory.get_url(self.fixture.cluster),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)


class CatalogUpdateTest(test.APITransactionTestCase):
    def setUp(self):
        super().setUp()
        self.fixture = fixtures.RancherFixture()
        self.catalog = factories.CatalogFactory(scope=self.fixture.cluster)
        self.url = factories.CatalogFactory.get_url(self.catalog)

    @utils.override_plugin_settings(READ_ONLY_MODE=True)
    def test_update_is_disabled_in_read_only_mode(self):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.patch(self.url, {'name': 'New name'})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch('waldur_rancher.backend.RancherBackend.client')
    def test_update_is_enabled_for_owner(self, mock_backend):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.patch(self.url, {'name': 'New name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CatalogDeleteTest(test.APITransactionTestCase):
    def setUp(self):
        super().setUp()
        self.fixture = fixtures.RancherFixture()
        self.catalog = factories.CatalogFactory(scope=self.fixture.cluster)
        self.url = factories.CatalogFactory.get_url(self.catalog)

    @utils.override_plugin_settings(READ_ONLY_MODE=True)
    def test_delete_is_disabled_in_read_only_mode(self):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch('waldur_rancher.backend.RancherBackend.client')
    def test_delete_is_enabled_for_owner(self, mock_backend):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
