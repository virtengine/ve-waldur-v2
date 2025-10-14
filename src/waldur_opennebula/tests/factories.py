import factory

from waldur_core.structure.tests.factories import ProjectFactory, ServiceSettingsFactory

from ..models import (
    OpenNebulaNetwork,
    OpenNebulaTenant,
    OpenNebulaVirtualMachine,
    OpenNebulaVolume,
)


class OpenNebulaTenantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OpenNebulaTenant

    name = factory.Sequence(lambda n: f"Tenant {n}")
    description = factory.Faker("sentence")
    backend_id = factory.Faker("uuid4")
    service_settings = factory.SubFactory(ServiceSettingsFactory, type="OpenNebula")
    project = factory.SubFactory(ProjectFactory)


class OpenNebulaVirtualMachineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OpenNebulaVirtualMachine

    name = factory.Sequence(lambda n: f"VM {n}")
    description = factory.Faker("sentence")
    tenant = factory.SubFactory(OpenNebulaTenantFactory)
    service_settings = factory.SelfAttribute("tenant.service_settings")
    project = factory.SelfAttribute("tenant.project")
    backend_id = factory.Faker("uuid4")
    cpu = 2
    ram = 2048
    disk = 20


class OpenNebulaNetworkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OpenNebulaNetwork

    name = factory.Sequence(lambda n: f"Network {n}")
    description = factory.Faker("sentence")
    backend_id = factory.Faker("uuid4")
    tenant = factory.SubFactory(OpenNebulaTenantFactory)
    service_settings = factory.SelfAttribute("tenant.service_settings")


class OpenNebulaVolumeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OpenNebulaVolume

    name = factory.Sequence(lambda n: f"Volume {n}")
    description = factory.Faker("sentence")
    backend_id = factory.Faker("uuid4")
    tenant = factory.SubFactory(OpenNebulaTenantFactory)
    service_settings = factory.SelfAttribute("tenant.service_settings")
    size = 10
