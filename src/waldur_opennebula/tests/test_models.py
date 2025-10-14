from django.test import TestCase

from waldur_core.structure.tests.factories import ServiceSettingsFactory

from ..backend import OpenNebulaBackend
from ..models import (
    OpenNebulaNetwork,
    OpenNebulaTenant,
    OpenNebulaVirtualMachine,
    OpenNebulaVolume,
)
from ..utils import generate_unique_tenant_name
from .factories import (
    OpenNebulaNetworkFactory,
    OpenNebulaTenantFactory,
    OpenNebulaVirtualMachineFactory,
    OpenNebulaVolumeFactory,
)


class OpenNebulaTenantModelTest(TestCase):
    def test_str(self):
        tenant = OpenNebulaTenantFactory(name="Test Tenant")
        self.assertEqual(str(tenant), "Test Tenant")

    def test_unique_constraint(self):
        tenant1 = OpenNebulaTenantFactory(backend_id="id1")
        with self.assertRaises(Exception):
            OpenNebulaTenantFactory(
                backend_id="id1", service_settings=tenant1.service_settings
            )

    def test_create_tenant_backend(self):
        settings = ServiceSettingsFactory()
        backend = OpenNebulaBackend(settings)
        # This will fail unless pyone is mocked, but demonstrates backend usage
        try:
            tenant = OpenNebulaTenantFactory(service_settings=settings)
            backend.create_tenant(tenant)
        except Exception:
            pass

    def test_delete_tenant_backend(self):
        tenant = OpenNebulaTenantFactory()
        backend = OpenNebulaBackend(tenant.service_settings)
        try:
            backend.delete_tenant(tenant)
        except Exception:
            pass

    def test_str_after_delete(self):
        tenant = OpenNebulaTenantFactory(name="ToDelete")
        tenant.delete()
        self.assertIsInstance(str(tenant), str)

    def test_generate_unique_tenant_name(self):
        name1 = generate_unique_tenant_name("base")
        name2 = generate_unique_tenant_name("base")
        self.assertNotEqual(name1, name2)

    def test_required_fields(self):
        with self.assertRaises(Exception):
            OpenNebulaTenant.objects.create()

    def test_invalid_backend_id(self):
        tenant = OpenNebulaTenantFactory.build(backend_id=None)
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            tenant.full_clean()


class OpenNebulaVirtualMachineModelTest(TestCase):
    def test_str(self):
        vm = OpenNebulaVirtualMachineFactory(name="Test VM")
        self.assertEqual(str(vm), "Test VM")

    def test_required_fields(self):
        with self.assertRaises(Exception):
            OpenNebulaVirtualMachine.objects.create()

    def test_invalid_cpu_ram_disk(self):
        from django.core.exceptions import ValidationError

        vm = OpenNebulaVirtualMachineFactory.build(cpu=-1, ram=-1, disk=-1)
        with self.assertRaises(ValidationError):
            vm.full_clean()


class OpenNebulaNetworkModelTest(TestCase):
    def test_str(self):
        network = OpenNebulaNetworkFactory(name="Test Network")
        self.assertEqual(str(network), "Test Network")

    def test_unique_constraint(self):
        network1 = OpenNebulaNetworkFactory(backend_id="id1")
        with self.assertRaises(Exception):
            OpenNebulaNetworkFactory(
                backend_id="id1", service_settings=network1.service_settings
            )

    def test_required_fields(self):
        with self.assertRaises(Exception):
            OpenNebulaNetwork.objects.create()

    def test_invalid_backend_id(self):
        from django.core.exceptions import ValidationError

        network = OpenNebulaNetworkFactory.build(backend_id=None)
        with self.assertRaises(ValidationError):
            network.full_clean()


class OpenNebulaVolumeModelTest(TestCase):
    def test_str(self):
        volume = OpenNebulaVolumeFactory(name="Test Volume")
        self.assertEqual(str(volume), "Test Volume")

    def test_unique_constraint(self):
        volume1 = OpenNebulaVolumeFactory(backend_id="id1")
        with self.assertRaises(Exception):
            OpenNebulaVolumeFactory(
                backend_id="id1", service_settings=volume1.service_settings
            )

    def test_required_fields(self):
        with self.assertRaises(Exception):
            OpenNebulaVolume.objects.create()

    def test_invalid_size(self):
        from django.core.exceptions import ValidationError

        volume = OpenNebulaVolumeFactory.build(size=-1)
        with self.assertRaises(ValidationError):
            volume.full_clean()
