from django.urls import reverse
from rest_framework.test import APITestCase  # noqa: F401
from .factories import (
    OpenNebulaTenantFactory,
    OpenNebulaVirtualMachineFactory,
    OpenNebulaNetworkFactory,
    OpenNebulaVolumeFactory,
)
from unittest import mock
from ..serializers import OpenNebulaVolumeSerializer, OpenNebulaNetworkSerializer
from ..models import OpenNebulaVolume, OpenNebulaNetwork
from django.contrib.auth import get_user_model
from django.test import Client
from waldur_core.structure.models import ServiceSettings

class OpenNebulaTenantViewSetTest(APITestCase):
    def setUp(self):
        self.tenant = OpenNebulaTenantFactory()
        self.url = reverse('opennebula-tenant-detail', args=[self.tenant.pk])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.set_tenant_quota')
    def test_set_quotas(self, mock_set_quota):
        mock_set_quota.return_value = True
        response = self.client.post(self.url + 'set_quotas/', {'quota_template': 'CPU=10'}, format='json')
        self.assertEqual(response.status_code, 200)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.get_tenant_quota')
    def test_pull_quotas(self, mock_get_quota):
        mock_get_quota.return_value = {'CPU': 10}
        response = self.client.get(self.url + 'pull_quotas/')
        self.assertEqual(response.status_code, 200)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.create_tenant')
    def test_create_tenant(self, mock_create_tenant):
        mock_create_tenant.return_value = OpenNebulaTenantFactory.build(name='tenant1')
        url = reverse('opennebulatenant-list')
        data = {'name': 'tenant1', 'description': 'desc', 'service_settings': self.tenant.service_settings.pk, 'project': self.tenant.project.pk}
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [201, 202])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.create_tenant')
    def test_create_tenant_missing_fields(self, mock_create_tenant):
        url = reverse('opennebulatenant-list')
        data = {'description': 'desc'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 400)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.delete_tenant')
    def test_delete_tenant(self, mock_delete_tenant):
        url = reverse('opennebula-tenant-detail', args=[self.tenant.pk])
        response = self.client.delete(url)
        self.assertIn(response.status_code, [204, 202])

    def test_get_tenant_not_found(self):
        url = reverse('opennebula-tenant-detail', args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

class OpenNebulaVirtualMachineViewSetTest(APITestCase):
    def setUp(self):
        self.vm = OpenNebulaVirtualMachineFactory()
        self.url = reverse('opennebula-vm-detail', args=[self.vm.pk])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.reboot_vm')
    def test_restart(self, mock_reboot):
        response = self.client.post(self.url + 'restart/')
        self.assertEqual(response.status_code, 202)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.resize_vm')
    def test_resize(self, mock_resize):
        response = self.client.post(self.url + 'resize/', {'cpu': 2, 'ram': 4096})
        self.assertEqual(response.status_code, 202)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.create_vm')
    def test_create_vm(self, mock_create_vm):
        mock_create_vm.return_value = OpenNebulaVirtualMachineFactory.build(name='vm1')
        url = reverse('opennebulavirtualmachine-list')
        data = {'name': 'vm1', 'tenant': self.vm.tenant.pk, 'service_settings': self.vm.service_settings.pk, 'project': self.vm.project.pk, 'cpu': 2, 'ram': 2048, 'disk': 20}
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [201, 202])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.create_vm')
    def test_create_vm_missing_fields(self, mock_create_vm):
        url = reverse('opennebulavirtualmachine-list')
        data = {'name': 'vm1'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 400)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.delete_vm')
    def test_delete_vm(self, mock_delete_vm):
        url = reverse('opennebula-vm-detail', args=[self.vm.pk])
        response = self.client.delete(url)
        self.assertIn(response.status_code, [204, 202])

    def test_get_vm_not_found(self):
        url = reverse('opennebula-vm-detail', args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

class OpenNebulaNetworkViewSetTest(APITestCase):
    def setUp(self):
        self.network = OpenNebulaNetworkFactory()
        self.url = reverse('opennebula-network-detail', args=[self.network.pk])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.update_network')
    def test_update_network(self, mock_update):
        response = self.client.post(self.url + 'update_network/', {'template': 'NAME=net1'})
        self.assertEqual(response.status_code, 202)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.update_network')
    def test_update_network_invalid_data(self, mock_update):
        response = self.client.post(self.url + 'update_network/', {'template': ''})
        self.assertEqual(response.status_code, 400)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.update_network')
    def test_update_network_not_found(self, mock_update):
        url = reverse('opennebula-network-detail', args=[99999])
        response = self.client.post(url + 'update_network/', {'template': 'NAME=net1'})
        self.assertEqual(response.status_code, 404)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.add_ar')
    def test_add_ar(self, mock_add_ar):
        response = self.client.post(self.url + 'add_ar/', {'ar_template': 'AR=1'})
        self.assertIn(response.status_code, [200, 202])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.rm_ar')
    def test_rm_ar(self, mock_rm_ar):
        response = self.client.post(self.url + 'rm_ar/', {'ar_id': '1', 'force': True})
        self.assertIn(response.status_code, [200, 202])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.update_ar')
    def test_update_ar(self, mock_update_ar):
        response = self.client.post(self.url + 'update_ar/', {'ar_template': 'AR=1'})
        self.assertIn(response.status_code, [200, 202])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.reserve_ar')
    def test_reserve_ar(self, mock_reserve_ar):
        response = self.client.post(self.url + 'reserve_ar/', {'reservation_template': 'RES=1'})
        self.assertIn(response.status_code, [200, 202])

class OpenNebulaVolumeViewSetTest(APITestCase):
    def setUp(self):
        self.volume = OpenNebulaVolumeFactory()
        self.vm = OpenNebulaVirtualMachineFactory()
        self.url = reverse('opennebula-volume-detail', args=[self.volume.pk])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.attach_disk_to_vm')
    def test_attach_to_vm(self, mock_attach):
        response = self.client.post(self.url + 'attach_to_vm/', {'vm_id': self.vm.pk, 'disk_template': 'IMAGE_ID=1'})
        self.assertEqual(response.status_code, 202)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.detach_disk_from_vm')
    def test_detach_from_vm(self, mock_detach):
        response = self.client.post(self.url + 'detach_from_vm/', {'vm_id': self.vm.pk, 'disk_id': 1})
        self.assertEqual(response.status_code, 202)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.delete_disk_snapshot')
    def test_delete_snapshot(self, mock_delete_snapshot):
        response = self.client.post(self.url + 'delete_snapshot/', {'vm_id': self.vm.pk, 'disk_id': 1, 'snapshot_id': 2})
        self.assertEqual(response.status_code, 202)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.revert_disk_snapshot')
    def test_revert_snapshot(self, mock_revert_snapshot):
        response = self.client.post(self.url + 'revert_snapshot/', {'vm_id': self.vm.pk, 'disk_id': 1, 'snapshot_id': 2})
        self.assertEqual(response.status_code, 202)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.rename_disk_snapshot')
    def test_rename_snapshot(self, mock_rename_snapshot):
        response = self.client.post(self.url + 'rename_snapshot/', {'vm_id': self.vm.pk, 'disk_id': 1, 'snapshot_id': 2, 'new_name': 'snap2'})
        self.assertEqual(response.status_code, 202)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.resize_disk')
    def test_resize(self, mock_resize_disk):
        response = self.client.post(self.url + 'resize/', {'vm_id': self.vm.pk, 'disk_id': 1, 'size': 100})
        self.assertEqual(response.status_code, 202)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.save_disk_as_image')
    def test_save_as_image(self, mock_save_as_image):
        response = self.client.post(self.url + 'save_as_image/', {'vm_id': self.vm.pk, 'disk_id': 1, 'image_name': 'img1'})
        self.assertEqual(response.status_code, 202)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.create_volume')
    def test_create_volume(self, mock_create_volume):
        mock_create_volume.return_value = OpenNebulaVolumeFactory.build(name='vol1')
        url = reverse('opennebulavolume-list')
        data = {'name': 'vol1', 'size': 10, 'tenant': self.vm.tenant.pk, 'service_settings': self.vm.service_settings.pk}
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [201, 202])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.create_volume')
    def test_create_volume_missing_fields(self, mock_create_volume):
        url = reverse('opennebulavolume-list')
        data = {'size': 10}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 400)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.create_volume')
    def test_create_volume_invalid_size(self, mock_create_volume):
        url = reverse('opennebulavolume-list')
        data = {'name': 'vol1', 'size': -1, 'tenant': self.vm.tenant.pk, 'service_settings': self.vm.service_settings.pk}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 400)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.delete_volume')
    def test_delete_volume(self, mock_delete_volume):
        url = reverse('opennebula-volume-detail', args=[self.volume.pk])
        response = self.client.delete(url)
        self.assertIn(response.status_code, [204, 202])

    def test_get_volume_not_found(self):
        url = reverse('opennebula-volume-detail', args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

class OpenNebulaVolumeSerializerTest(APITestCase):
    def test_required_fields(self):
        serializer = OpenNebulaVolumeSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
        self.assertIn('tenant', serializer.errors)
        self.assertIn('service_settings', serializer.errors)
        self.assertIn('size', serializer.errors)

    def test_invalid_size(self):
        serializer = OpenNebulaVolumeSerializer(data={'name': 'vol', 'size': -1, 'tenant': 1, 'service_settings': 1})
        self.assertFalse(serializer.is_valid())
        self.assertIn('size', serializer.errors)

class OpenNebulaNetworkSerializerTest(APITestCase):
    def test_required_fields(self):
        serializer = OpenNebulaNetworkSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
        self.assertIn('service_settings', serializer.errors)

    def test_invalid_backend_id(self):
        serializer = OpenNebulaNetworkSerializer(data={'name': 'net', 'backend_id': None, 'service_settings': 1})
        self.assertTrue(serializer.is_valid())  # backend_id is blank=True, so None is allowed 

class OpenNebulaPermissionTest(APITestCase):
    def setUp(self):
        self.tenant = OpenNebulaTenantFactory()
        self.vm = OpenNebulaVirtualMachineFactory()
        self.network = OpenNebulaNetworkFactory()
        self.volume = OpenNebulaVolumeFactory()
        self.client.logout()

    def test_tenant_create_permission(self):
        url = reverse('opennebulatenant-list')
        data = {'name': 'tenant1', 'description': 'desc', 'service_settings': self.tenant.service_settings.pk, 'project': self.tenant.project.pk}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 403)

    def test_tenant_delete_permission(self):
        url = reverse('opennebula-tenant-detail', args=[self.tenant.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

    def test_vm_create_permission(self):
        url = reverse('opennebulavirtualmachine-list')
        data = {'name': 'vm1', 'tenant': self.vm.tenant.pk, 'service_settings': self.vm.service_settings.pk, 'project': self.vm.project.pk, 'cpu': 2, 'ram': 2048, 'disk': 20}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 403)

    def test_vm_delete_permission(self):
        url = reverse('opennebula-vm-detail', args=[self.vm.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

    def test_network_create_permission(self):
        url = reverse('opennebulanetwork-list')
        data = {'name': 'net1', 'service_settings': self.network.service_settings.pk}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 403)

    def test_network_delete_permission(self):
        url = reverse('opennebula-network-detail', args=[self.network.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

    def test_volume_create_permission(self):
        url = reverse('opennebulavolume-list')
        data = {'name': 'vol1', 'size': 10, 'tenant': self.volume.tenant.pk, 'service_settings': self.volume.service_settings.pk}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 403)

    def test_volume_delete_permission(self):
        url = reverse('opennebula-volume-detail', args=[self.volume.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

class OpenNebulaMethodNotAllowedTest(APITestCase):
    def setUp(self):
        self.tenant = OpenNebulaTenantFactory()
        self.vm = OpenNebulaVirtualMachineFactory()
        self.network = OpenNebulaNetworkFactory()
        self.volume = OpenNebulaVolumeFactory()

    def test_tenant_put_on_list(self):
        url = reverse('opennebulatenant-list')
        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 405)

    def test_tenant_post_on_detail(self):
        url = reverse('opennebula-tenant-detail', args=[self.tenant.pk])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 405)

    def test_vm_put_on_list(self):
        url = reverse('opennebulavirtualmachine-list')
        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 405)

    def test_vm_post_on_detail(self):
        url = reverse('opennebula-vm-detail', args=[self.vm.pk])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 405)

    def test_network_put_on_list(self):
        url = reverse('opennebulanetwork-list')
        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 405)

    def test_network_post_on_detail(self):
        url = reverse('opennebula-network-detail', args=[self.network.pk])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 405)

    def test_volume_put_on_list(self):
        url = reverse('opennebulavolume-list')
        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 405)

    def test_volume_post_on_detail(self):
        url = reverse('opennebula-volume-detail', args=[self.volume.pk])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 405)

class OpenNebulaAdminIntegrationTest(APITestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser('admin', 'admin@example.com', 'password')
        self.client = Client()
        self.client.login(username='admin', password='password')
        self.tenant = OpenNebulaTenantFactory()
        self.vm = OpenNebulaVirtualMachineFactory()
        self.network = OpenNebulaNetworkFactory()
        self.volume = OpenNebulaVolumeFactory()

    def test_tenant_admin_changelist(self):
        url = '/admin/waldur_opennebula/opennebulatenant/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_tenant_admin_detail(self):
        url = f'/admin/waldur_opennebula/opennebulatenant/{self.tenant.pk}/change/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_vm_admin_changelist(self):
        url = '/admin/waldur_opennebula/opennebulavirtualmachine/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_vm_admin_detail(self):
        url = f'/admin/waldur_opennebula/opennebulavirtualmachine/{self.vm.pk}/change/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_network_admin_changelist(self):
        url = '/admin/waldur_opennebula/opennebulanetwork/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_network_admin_detail(self):
        url = f'/admin/waldur_opennebula/opennebulanetwork/{self.network.pk}/change/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_volume_admin_changelist(self):
        url = '/admin/waldur_opennebula/opennebulavolume/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_volume_admin_detail(self):
        url = f'/admin/waldur_opennebula/opennebulavolume/{self.volume.pk}/change/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

class OpenNebulaAPIConnectivityTest(APITestCase):
    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.ping')
    def test_api_ping_success(self, mock_ping):
        mock_ping.return_value = True
        url = reverse('opennebula-api-ping') if 'opennebula-api-ping' in self.client.handler._view_name_func_map else '/api/opennebula/ping/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 202])
        self.assertIn('success', response.data)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.ping')
    def test_api_ping_failure(self, mock_ping):
        mock_ping.return_value = False
        url = reverse('opennebula-api-ping') if 'opennebula-api-ping' in self.client.handler._view_name_func_map else '/api/opennebula/ping/'
        response = self.client.get(url)
        self.assertIn(response.status_code, [400, 503, 500])
        self.assertIn('error', response.data)

class OpenNebulaVirtualMachineBackupViewSetTest(APITestCase):
    def setUp(self):
        self.vm = OpenNebulaVirtualMachineFactory()
        self.url = reverse('opennebula-vm-detail', args=[self.vm.pk])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.backup_vm')
    def test_backup_vm(self, mock_backup_vm):
        response = self.client.post(self.url + 'backup/', {'ds_id': 10, 'reset': True})
        self.assertIn(response.status_code, [202, 200])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.backup_vm')
    def test_backup_vm_missing_ds_id(self, mock_backup_vm):
        response = self.client.post(self.url + 'backup/', {'reset': True})
        self.assertEqual(response.status_code, 400)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.backup_cancel')
    def test_backup_cancel(self, mock_backup_cancel):
        response = self.client.post(self.url + 'backup_cancel/')
        self.assertIn(response.status_code, [202, 200])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.restore_vm')
    def test_restore_vm(self, mock_restore_vm):
        response = self.client.post(self.url + 'restore/', {'backup_id': 123, 'in_place': False})
        self.assertIn(response.status_code, [202, 200])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.restore_vm')
    def test_restore_vm_missing_backup_id(self, mock_restore_vm):
        response = self.client.post(self.url + 'restore/', {'in_place': True})
        self.assertEqual(response.status_code, 400)

class OpenNebulaTenantImportSyncTest(APITestCase):
    def setUp(self):
        self.tenant = OpenNebulaTenantFactory()
        self.url = reverse('opennebula-tenant-detail', args=[self.tenant.pk])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.pull_vms')
    def test_backend_vms(self, mock_pull_vms):
        mock_pull_vms.return_value = [OpenNebulaVirtualMachineFactory.build()]
        response = self.client.get(self.url + 'backend_vms/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('name', response.data[0])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.pull_volumes')
    def test_backend_volumes(self, mock_pull_volumes):
        mock_pull_volumes.return_value = [OpenNebulaVolumeFactory.build()]
        response = self.client.get(self.url + 'backend_volumes/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('name', response.data[0])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.pull_networks')
    def test_backend_networks(self, mock_pull_networks):
        mock_pull_networks.return_value = [OpenNebulaNetworkFactory.build()]
        response = self.client.get(self.url + 'backend_networks/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('name', response.data[0])

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.pull_vms')
    def test_backend_vms_error(self, mock_pull_vms):
        mock_pull_vms.side_effect = Exception('Backend error')
        response = self.client.get(self.url + 'backend_vms/')
        self.assertEqual(response.status_code, 500)
        self.assertIn('detail', response.data)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.pull_volumes')
    def test_backend_volumes_error(self, mock_pull_volumes):
        mock_pull_volumes.side_effect = Exception('Backend error')
        response = self.client.get(self.url + 'backend_volumes/')
        self.assertEqual(response.status_code, 500)
        self.assertIn('detail', response.data)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.pull_networks')
    def test_backend_networks_error(self, mock_pull_networks):
        mock_pull_networks.side_effect = Exception('Backend error')
        response = self.client.get(self.url + 'backend_networks/')
        self.assertEqual(response.status_code, 500)
        self.assertIn('detail', response.data)

class OpenNebulaVMWizardEndpointsTest(APITestCase):
    def setUp(self):
        self.settings = ServiceSettings.objects.create(
            type='OpenNebula', backend_url='http://localhost', username='user', password='pass', name='test')
        self.templates_url = reverse('opennebula-template-list')
        self.images_url = reverse('opennebula-image-list')
        self.networks_url = reverse('opennebula-network-list')
        self.create_url = reverse('opennebula-vm-create')

    @mock.patch('waldur_opennebula.client.OpenNebulaClient.list_templates')
    def test_list_templates(self, mock_list_templates):
        mock_list_templates.return_value = type('obj', (), {'VMTEMPLATE': [type('tmpl', (), {'ID': 1, 'NAME': 'tmpl1', 'TEMPLATE': type('t', (), {'CPU': 2, 'MEMORY': 4096})()})()]})()
        response = self.client.get(self.templates_url, {'service_settings': self.settings.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['name'], 'tmpl1')

    @mock.patch('waldur_opennebula.client.OpenNebulaClient.list_images')
    def test_list_images(self, mock_list_images):
        mock_list_images.return_value = type('obj', (), {'IMAGE': [type('img', (), {'ID': 1, 'NAME': 'img1', 'SIZE': 10, 'TYPE': 'OS'})()]})()
        response = self.client.get(self.images_url, {'service_settings': self.settings.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['name'], 'img1')

    @mock.patch('waldur_opennebula.client.OpenNebulaClient.list_networks')
    def test_list_networks(self, mock_list_networks):
        mock_list_networks.return_value = type('obj', (), {'VNET': [type('net', (), {'ID': 1, 'NAME': 'net1', 'BRIDGE': 'br0', 'VLAN_ID': 100})()]})()
        response = self.client.get(self.networks_url, {'service_settings': self.settings.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['name'], 'net1')

    @mock.patch('waldur_opennebula.client.OpenNebulaClient.create_vm')
    def test_create_vm_success(self, mock_create_vm):
        mock_create_vm.return_value = 123
        data = {
            'service_settings': self.settings.pk,
            'template_id': 1,
            'name': 'test-vm',
            'networks': [1],
            'cpu': 2,
            'ram': 4096,
            'disk': 20,
            'ssh_key': 'ssh-rsa AAA...',
            'contextualization': True,
            'extra': {'CUSTOM': 'value'}
        }
        response = self.client.post(self.create_url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['vm_id'], 123)

    def test_create_vm_missing_fields(self):
        data = {'name': 'test-vm'}
        response = self.client.post(self.create_url, data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('service_settings', response.data)
        self.assertIn('template_id', response.data)
        self.assertIn('networks', response.data)

    @mock.patch('waldur_opennebula.client.OpenNebulaClient.create_vm')
    def test_create_vm_backend_error(self, mock_create_vm):
        mock_create_vm.side_effect = Exception('Backend error')
        data = {
            'service_settings': self.settings.pk,
            'template_id': 1,
            'name': 'test-vm',
            'networks': [1],
        }
        response = self.client.post(self.create_url, data, format='json')
        self.assertEqual(response.status_code, 500)
        self.assertIn('detail', response.data)

class OpenNebulaVMMigrationAndDiskManagementTest(APITestCase):
    def setUp(self):
        self.vm = OpenNebulaVirtualMachineFactory()
        self.migrate_url = reverse('opennebula-vm-migrate')
        self.attach_disk_url = reverse('opennebula-vm-attach-disk')
        self.resize_disk_url = reverse('opennebula-vm-resize-disk')
        self.save_disk_as_image_url = reverse('opennebula-vm-save-disk-as-image')

    @mock.patch('waldur_opennebula.tasks.migrate_vm_task.delay')
    def test_migrate_vm(self, mock_task):
        data = {'vm': self.vm.pk, 'host_id': 42, 'live': True, 'enforce': False, 'ds_id': None, 'migration_type': 0}
        response = self.client.post(self.migrate_url, data, format='json')
        self.assertEqual(response.status_code, 202)
        mock_task.assert_called_once()

    def test_migrate_vm_missing_fields(self):
        response = self.client.post(self.migrate_url, {'host_id': 42}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('vm', response.data)

    @mock.patch('waldur_opennebula.tasks.attach_disk_task.delay')
    def test_attach_disk(self, mock_task):
        data = {'vm': self.vm.pk, 'image_id': 1, 'size': 10, 'type': 'DATABLOCK', 'target': 'vdb'}
        response = self.client.post(self.attach_disk_url, data, format='json')
        self.assertEqual(response.status_code, 202)
        mock_task.assert_called_once()

    def test_attach_disk_missing_fields(self):
        response = self.client.post(self.attach_disk_url, {'image_id': 1}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('vm', response.data)

    @mock.patch('waldur_opennebula.tasks.resize_disk_task.delay')
    def test_resize_disk(self, mock_task):
        data = {'vm': self.vm.pk, 'disk_id': 2, 'size': 100}
        response = self.client.post(self.resize_disk_url, data, format='json')
        self.assertEqual(response.status_code, 202)
        mock_task.assert_called_once()

    def test_resize_disk_missing_fields(self):
        response = self.client.post(self.resize_disk_url, {'disk_id': 2}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('vm', response.data)
        self.assertIn('size', response.data)

    @mock.patch('waldur_opennebula.tasks.save_disk_as_image_task.delay')
    def test_save_disk_as_image(self, mock_task):
        data = {'vm': self.vm.pk, 'disk_id': 2, 'image_name': 'backup-img', 'image_type': 'OS', 'snapshot_id': 5}
        response = self.client.post(self.save_disk_as_image_url, data, format='json')
        self.assertEqual(response.status_code, 202)
        mock_task.assert_called_once()

    def test_save_disk_as_image_missing_fields(self):
        response = self.client.post(self.save_disk_as_image_url, {'disk_id': 2}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('vm', response.data)
        self.assertIn('image_name', response.data)

class OpenNebulaVMSnapshotAndBackupTest(APITestCase):
    def setUp(self):
        self.vm = OpenNebulaVirtualMachineFactory()
        self.snapshot_url = reverse('opennebulavmsnapshotview')
        self.list_snapshots_url = reverse('opennebulavmlistsnapshotsview')
        self.create_backup_url = reverse('opennebulabackupcreateview')
        self.list_backups_url = reverse('opennebulabackuplistview')
        self.restore_backup_url = reverse('opennebularestorebackupview')

    @mock.patch('waldur_opennebula.tasks.create_vm_snapshot_task.delay')
    def test_create_snapshot(self, mock_task):
        data = {'vm': self.vm.pk, 'name': 'snap1'}
        response = self.client.post(self.snapshot_url, data, format='json')
        self.assertEqual(response.status_code, 202)
        mock_task.assert_called_once()

    def test_create_snapshot_missing_fields(self):
        response = self.client.post(self.snapshot_url, {'name': 'snap1'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('vm', response.data)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.list_snapshots')
    def test_list_snapshots(self, mock_list_snapshots):
        mock_list_snapshots.return_value = [{'id': 1, 'name': 'snap1'}]
        response = self.client.get(self.list_snapshots_url, {'vm': self.vm.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['name'], 'snap1')

    @mock.patch('waldur_opennebula.tasks.create_backup_task.delay')
    def test_create_backup(self, mock_task):
        data = {'vm': self.vm.pk, 'name': 'backup1', 'description': 'desc'}
        response = self.client.post(self.create_backup_url, data, format='json')
        self.assertEqual(response.status_code, 202)
        mock_task.assert_called_once()

    def test_create_backup_missing_fields(self):
        response = self.client.post(self.create_backup_url, {'name': 'backup1'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('vm', response.data)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.list_backups')
    def test_list_backups(self, mock_list_backups):
        mock_list_backups.return_value = [{'id': 1, 'name': 'backup1'}]
        response = self.client.get(self.list_backups_url, {'vm': self.vm.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['name'], 'backup1')

    @mock.patch('waldur_opennebula.tasks.restore_backup_task.delay')
    def test_restore_backup(self, mock_task):
        data = {'backup_id': 'b1', 'vm': self.vm.pk, 'in_place': True, 'new_vm_name': ''}
        response = self.client.post(self.restore_backup_url, data, format='json')
        self.assertEqual(response.status_code, 202)
        mock_task.assert_called_once()

    def test_restore_backup_missing_fields(self):
        response = self.client.post(self.restore_backup_url, {'backup_id': 'b1'}, format='json')
        self.assertEqual(response.status_code, 202)  # new_vm_name is optional, vm is optional for new VM 

class OpenNebulaFloatingIPAndMarketplaceTest(APITestCase):
    def setUp(self):
        self.vm = OpenNebulaVirtualMachineFactory()
        self.assign_url = reverse('opennebula-floatingip-assign')
        self.release_url = reverse('opennebula-floatingip-release')
        self.offerings_url = reverse('opennebula-marketplace-offering-list')

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.assign_floating_ip')
    def test_assign_floating_ip(self, mock_assign):
        mock_assign.return_value = {'vm_id': self.vm.backend_id, 'network_id': 1, 'ip_address': '10.0.0.1'}
        data = {'vm': self.vm.pk, 'network_id': 1, 'ip_address': '10.0.0.1'}
        response = self.client.post(self.assign_url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['ip_address'], '10.0.0.1')

    def test_assign_floating_ip_missing_fields(self):
        response = self.client.post(self.assign_url, {'network_id': 1}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('vm', response.data)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.release_floating_ip')
    def test_release_floating_ip(self, mock_release):
        mock_release.return_value = {'vm_id': self.vm.backend_id, 'ip_address': '10.0.0.1', 'released': True}
        data = {'vm': self.vm.pk, 'ip_address': '10.0.0.1'}
        response = self.client.post(self.release_url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['released'])

    def test_release_floating_ip_missing_fields(self):
        response = self.client.post(self.release_url, {'ip_address': '10.0.0.1'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('vm', response.data)

    @mock.patch('waldur_opennebula.backend.OpenNebulaBackend.list_marketplace_offerings')
    def test_list_marketplace_offerings(self, mock_list):
        mock_list.return_value = [
            {'id': 1, 'name': 'tmpl1', 'template_id': 1, 'cpu': 2, 'ram': 4096, 'disk': 20, 'category': 'General', 'extra': {}}
        ]
        response = self.client.get(self.offerings_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['name'], 'tmpl1') 