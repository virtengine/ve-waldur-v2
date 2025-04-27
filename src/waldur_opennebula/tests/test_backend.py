import unittest
from unittest import mock
from waldur_core.structure.tests.factories import ServiceSettingsFactory
from ..backend import OpenNebulaBackend
from ..models import OpenNebulaTenant, OpenNebulaVolume, OpenNebulaNetwork
from .. import models

class OpenNebulaBackendVolumeTest(unittest.TestCase):
    def setUp(self):
        self.settings = ServiceSettingsFactory()
        self.backend = OpenNebulaBackend(self.settings)
        self.backend.client = mock.Mock()
        self.tenant = mock.Mock(spec=OpenNebulaTenant)
        self.tenant.backend_id = '1'
        self.tenant.project = None
        self.tenant.service_settings = self.settings

    def test_pull_volumes(self):
        self.backend.client.list_volumes.return_value = [mock.Mock(ID=1, NAME='vol1', DESCRIPTION='desc', SIZE=10)]
        result = self.backend.pull_volumes(self.tenant)
        self.assertEqual(len(result), 1)
        self.backend.client.list_volumes.assert_called_once()

    def test_create_volume(self):
        self.backend.client.create_volume.return_value = 1
        self.backend.client.get_volume.return_value = mock.Mock(ID=1, NAME='vol1', DESCRIPTION='desc', SIZE=10)
        vol = self.backend.create_volume(self.tenant, 'vol1', 10, 'desc')
        self.assertEqual(vol.name, 'vol1')
        self.backend.client.create_volume.assert_called_once_with('vol1', 10, 'desc')

    def test_delete_volume(self):
        volume = mock.Mock(spec=OpenNebulaVolume)
        volume.backend_id = '1'
        self.backend.delete_volume(volume)
        self.backend.client.delete_volume.assert_called_once_with('1')

    def test_attach_and_detach_disk(self):
        vm = mock.Mock()
        vm.backend_id = 'vm1'
        volume = mock.Mock()
        volume.backend_id = 'vol1'
        self.backend.attach_disk(vm, volume)
        self.backend.client.attach_disk.assert_called_once_with('vm1', 'vol1')
        self.backend.detach_disk(vm, 'disk1')
        self.backend.client.detach_disk.assert_called_once_with('vm1', 'disk1')

    def test_snapshot_and_restore(self):
        vm = mock.Mock()
        vm.backend_id = 'vm1'
        self.backend.snapshot_vm(vm, 'snap')
        self.backend.client.snapshot_vm.assert_called_once_with('vm1', 'snap')
        self.backend.restore_vm_snapshot(vm, 'snap1')
        self.backend.client.restore_vm_snapshot.assert_called_once_with('vm1', 'snap1')

    def test_resize_and_save_as_image(self):
        vm = mock.Mock()
        vm.backend_id = 'vm1'
        self.backend.resize_disk(vm, 'disk1', 20)
        self.backend.client.resize_disk.assert_called_once_with('vm1', 'disk1', 20)
        self.backend.save_disk_as_image(vm, 'disk1', 'img')
        self.backend.client.save_disk_as_image.assert_called_once_with('vm1', 'disk1', 'img', '', -1)

class OpenNebulaBackendNetworkTest(unittest.TestCase):
    def setUp(self):
        self.settings = ServiceSettingsFactory()
        self.backend = OpenNebulaBackend(self.settings)
        self.backend.client = mock.Mock()
        self.network = mock.Mock(spec=OpenNebulaNetwork)
        self.network.backend_id = 'net1'

    def test_update_network(self):
        self.backend.update_network(self.network, 'template')
        self.backend.client.update_network.assert_called_once_with('net1', 'template')

    def test_add_ar(self):
        self.backend.add_ar(self.network, 'ar_template')
        self.backend.client.add_ar.assert_called_once_with('net1', 'ar_template')

    def test_rm_ar(self):
        self.backend.rm_ar(self.network, 'ar_id', True)
        self.backend.client.rm_ar.assert_called_once_with('net1', 'ar_id', True)

    def test_update_ar(self):
        self.backend.update_ar(self.network, 'ar_template')
        self.backend.client.update_ar.assert_called_once_with('net1', 'ar_template')

    def test_reserve_ar(self):
        self.backend.reserve_ar(self.network, 'reservation_template')
        self.backend.client.reserve_ar.assert_called_once_with('net1', 'reservation_template')

class OpenNebulaBackendTenantTest(unittest.TestCase):
    def setUp(self):
        self.settings = ServiceSettingsFactory()
        self.backend = OpenNebulaBackend(self.settings)
        self.backend.client = mock.Mock()
        self.tenant = mock.Mock(spec=OpenNebulaTenant)
        self.tenant.backend_id = '1'
        self.tenant.project = None
        self.tenant.service_settings = self.settings

    def test_pull_tenants(self):
        self.backend.client.list_groups.return_value = [mock.Mock(ID=1, NAME='tenant1', DESCRIPTION='desc')]
        result = self.backend.pull_tenants()
        self.assertEqual(len(result), 1)
        self.backend.client.list_groups.assert_called_once()

    def test_create_tenant(self):
        self.backend.client.create_group.return_value = 1
        self.backend.client.get_group.return_value = mock.Mock(ID=1, NAME='tenant1', DESCRIPTION='desc')
        tenant = self.backend.create_tenant('tenant1', 'desc')
        self.assertEqual(tenant.name, 'tenant1')
        self.backend.client.create_group.assert_called_once_with('tenant1', 'desc')

    def test_delete_tenant(self):
        self.backend.delete_tenant(self.tenant)
        self.backend.client.delete_group.assert_called_once_with('1')

    def test_set_and_get_quota(self):
        self.backend.set_tenant_quota(self.tenant, {'CPU': 10})
        self.backend.client.set_group_quota.assert_called_once_with(1, {'CPU': 10})
        self.backend.get_tenant_quota(self.tenant)
        self.backend.client.get_group_quota.assert_called_once_with(1)

class OpenNebulaBackendVMTest(unittest.TestCase):
    def setUp(self):
        self.settings = ServiceSettingsFactory()
        self.backend = OpenNebulaBackend(self.settings)
        self.backend.client = mock.Mock()
        self.tenant = mock.Mock(spec=OpenNebulaTenant)
        self.tenant.backend_id = '1'
        self.tenant.project = None
        self.tenant.service_settings = self.settings
        self.vm = mock.Mock()
        self.vm.backend_id = 'vm1'
        self.vm.tenant = self.tenant
        self.vm.project = None
        self.vm.service_settings = self.settings

    def test_pull_vms(self):
        self.backend.client.list_vms.return_value = [mock.Mock(ID=1, NAME='vm1', TEMPLATE=mock.Mock(CPU=2, MEMORY=2048))]
        result = self.backend.pull_vms(self.tenant)
        self.assertEqual(len(result), 1)
        self.backend.client.list_vms.assert_called_once()

    def test_create_vm(self):
        self.backend.client.create_vm.return_value = 1
        self.backend.client.get_vm.return_value = mock.Mock(ID=1, NAME='vm1', TEMPLATE=mock.Mock(CPU=2, MEMORY=2048))
        vm = self.backend.create_vm(self.tenant, 'vm1', template_id=1, cpu=2, ram=2048, disk=20)
        self.assertEqual(vm.name, 'vm1')
        self.backend.client.create_vm.assert_called_once()

    def test_delete_vm(self):
        self.backend.delete_vm(self.vm)
        self.backend.client.delete_vm.assert_called_once_with('vm1')

    def test_start_stop_vm(self):
        self.backend.start_vm(self.vm)
        self.backend.client.start_vm.assert_called_once_with('vm1')
        self.backend.stop_vm(self.vm)
        self.backend.client.stop_vm.assert_called_once_with('vm1')

    def test_reboot_and_resize_vm(self):
        self.backend.reboot_vm(self.vm)
        self.backend.client.reboot_vm.assert_called_once_with('vm1')
        self.backend.resize_vm(self.vm, cpu=4, ram=4096)
        self.backend.client.resize_vm.assert_called_once_with('vm1', cpu=4, ram=4096)

    def test_snapshot_and_restore(self):
        self.backend.snapshot_vm(self.vm, 'snap')
        self.backend.client.snapshot_vm.assert_called_once_with('vm1', 'snap')
        self.backend.restore_vm_snapshot(self.vm, 'snap1')
        self.backend.client.restore_vm_snapshot.assert_called_once_with('vm1', 'snap1')

    def test_get_console(self):
        self.backend.get_console(self.vm)
        self.backend.client.get_console.assert_called_once_with('vm1')

class OpenNebulaBackendBackupTest(unittest.TestCase):
    def setUp(self):
        self.settings = ServiceSettingsFactory()
        self.backend = OpenNebulaBackend(self.settings)
        self.backend.client = mock.Mock()
        self.vm = mock.Mock()
        self.vm.backend_id = 'vm1'
        self.vm.service_settings = self.settings

    def test_backup_vm(self):
        self.backend.backup_vm(self.vm, ds_id=10, reset=True)
        self.backend.client.backup_vm.assert_called_once_with('vm1', 10, True)

    def test_backup_cancel(self):
        self.backend.backup_cancel(self.vm)
        self.backend.client.backup_cancel.assert_called_once_with('vm1')

    def test_restore_vm(self):
        self.backend.restore_vm(self.vm, backup_id=123, in_place=False)
        self.backend.client.restore_vm.assert_called_once_with('vm1', 123, False) 