import uuid
from random import randint

import factory
import pytz
from django.urls import reverse
from django.utils import timezone
from factory import fuzzy

from waldur_core.structure import models as structure_models
from waldur_core.structure.tests import factories as structure_factories
from waldur_openstack.openstack.tests import factories as openstack_factories

from .. import models


class OpenStackTenantServiceSettingsFactory(structure_factories.ServiceSettingsFactory):
    class Meta:
        model = structure_models.ServiceSettings
        exclude = ('tenant',)

    name = factory.SelfAttribute('tenant.name')
    scope = factory.SelfAttribute('tenant')
    customer = factory.SelfAttribute('tenant.customer')
    backend_url = factory.SelfAttribute(
        'tenant.service_project_link.service.settings.backend_url'
    )
    username = factory.SelfAttribute('tenant.user_username')
    password = factory.SelfAttribute('tenant.user_password')
    type = 'OpenStackTenant'
    tenant = factory.SubFactory(openstack_factories.TenantFactory)
    options = {'tenant_id': uuid.uuid4()}


class OpenStackTenantServiceFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.OpenStackTenantService

    settings = factory.SubFactory(OpenStackTenantServiceSettingsFactory)
    customer = factory.SelfAttribute('settings.customer')

    @classmethod
    def get_url(cls, service=None, action=None):
        if service is None:
            service = OpenStackTenantServiceSettingsFactory()
        url = 'http://testserver' + reverse(
            'openstacktenant-detail', kwargs={'uuid': service.uuid.hex}
        )
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('openstacktenant-list')


class OpenStackTenantServiceProjectLinkFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.OpenStackTenantServiceProjectLink

    service = factory.SubFactory(OpenStackTenantServiceFactory)
    project = factory.SubFactory(structure_factories.ProjectFactory)

    @classmethod
    def get_url(cls, spl=None, action=None):
        if spl is None:
            spl = OpenStackTenantServiceProjectLinkFactory()
        url = 'http://testserver' + reverse(
            'openstacktenant-spl-detail', kwargs={'pk': spl.pk}
        )
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('openstacktenant-spl-list')


class FlavorFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Flavor

    name = factory.Sequence(lambda n: 'flavor%s' % n)
    settings = factory.SubFactory(structure_factories.ServiceSettingsFactory)

    cores = 2
    ram = 2 * 1024
    disk = 10 * 1024

    backend_id = factory.Sequence(lambda n: 'flavor-id%s' % n)

    @classmethod
    def get_url(cls, flavor=None):
        if flavor is None:
            flavor = FlavorFactory()
        return 'http://testserver' + reverse(
            'openstacktenant-flavor-detail', kwargs={'uuid': flavor.uuid.hex}
        )

    @classmethod
    def get_list_url(cls, action):
        url = 'http://testserver' + reverse('openstacktenant-flavor-list')
        return url if action is None else url + action + '/'


class ImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Image

    name = factory.Sequence(lambda n: 'image%s' % n)
    settings = factory.SubFactory(structure_factories.ServiceSettingsFactory)

    backend_id = factory.Sequence(lambda n: 'image-id%s' % n)

    @classmethod
    def get_url(cls, image=None):
        if image is None:
            image = ImageFactory()
        return 'http://testserver' + reverse(
            'openstacktenant-image-detail', kwargs={'uuid': image.uuid.hex}
        )

    @classmethod
    def get_list_url(cls, action=None):
        url = 'http://testserver' + reverse('openstacktenant-image-list')
        return url if action is None else url + action + '/'


class VolumeFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Volume

    name = factory.Sequence(lambda n: 'volume%s' % n)
    service_project_link = factory.SubFactory(OpenStackTenantServiceProjectLinkFactory)
    size = 10 * 1024
    backend_id = factory.LazyAttribute(lambda _: str(uuid.uuid4()))

    @classmethod
    def get_url(cls, instance=None, action=None):
        if instance is None:
            instance = InstanceFactory()
        url = 'http://testserver' + reverse(
            'openstacktenant-volume-detail', kwargs={'uuid': instance.uuid.hex}
        )
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls, action=None):
        url = 'http://testserver' + reverse('openstacktenant-volume-list')
        return url if action is None else url + action + '/'


class InstanceAvailabilityZoneFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.InstanceAvailabilityZone

    name = factory.Sequence(lambda n: 'instance_availability_zone_%s' % n)
    settings = factory.SubFactory(OpenStackTenantServiceSettingsFactory)

    @classmethod
    def get_url(cls, instance=None):
        if instance is None:
            instance = InstanceAvailabilityZoneFactory()
        return 'http://testserver' + reverse(
            'openstacktenant-instance-availability-zone-detail',
            kwargs={'uuid': instance.uuid.hex},
        )

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse(
            'openstacktenant-instance-availability-zone-list'
        )


class InstanceFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Instance

    name = factory.Sequence(lambda n: 'instance%s' % n)
    service_project_link = factory.SubFactory(OpenStackTenantServiceProjectLinkFactory)
    backend_id = factory.Sequence(lambda n: 'backend_id_%s' % n)
    ram = 2048

    @classmethod
    def get_url(cls, instance=None, action=None):
        if instance is None:
            instance = InstanceFactory()
        url = 'http://testserver' + reverse(
            'openstacktenant-instance-detail', kwargs={'uuid': instance.uuid.hex}
        )
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls, action=None):
        url = 'http://testserver' + reverse('openstacktenant-instance-list')
        return url if action is None else url + action + '/'

    @factory.post_generation
    def volumes(self, create, extracted, **kwargs):
        if not create:
            return

        self.volumes.create(
            backend_id='{0}-system'.format(self.name),
            service_project_link=self.service_project_link,
            bootable=True,
            size=10 * 1024,
            name='{0}-system'.format(self.name),
            image_name='{0}-image-name'.format(self.name)
            if not kwargs
            else kwargs['image_name'],
        )
        self.volumes.create(
            backend_id='{0}-data'.format(self.name),
            service_project_link=self.service_project_link,
            size=20 * 1024,
            name='{0}-data'.format(self.name),
            state=models.Volume.States.OK,
        )

    @factory.post_generation
    def security_groups(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for group in extracted:
                self.security_groups.add(group)


class FloatingIPFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.FloatingIP

    name = factory.Sequence(lambda n: 'floating_ip%s' % n)
    settings = factory.SubFactory(OpenStackTenantServiceSettingsFactory)
    runtime_state = factory.Iterator(['ACTIVE', 'DOWN'])
    address = factory.LazyAttribute(
        lambda o: '.'.join('%s' % randint(0, 255) for _ in range(4))  # noqa: S311
    )
    backend_id = factory.Sequence(lambda n: 'backend_id_%s' % n)

    @classmethod
    def get_url(cls, instance=None):
        if instance is None:
            instance = FloatingIPFactory()
        return 'http://testserver' + reverse(
            'openstacktenant-fip-detail', kwargs={'uuid': instance.uuid.hex}
        )

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('openstacktenant-fip-list')


class SecurityGroupFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.SecurityGroup

    name = factory.Sequence(lambda n: 'security_group%s' % n)
    settings = factory.SubFactory(OpenStackTenantServiceSettingsFactory)
    backend_id = factory.Sequence(lambda n: 'backend_id_%s' % n)

    @classmethod
    def get_url(cls, sgp=None):
        if sgp is None:
            sgp = SecurityGroupFactory()
        return 'http://testserver' + reverse(
            'openstacktenant-sgp-detail', kwargs={'uuid': sgp.uuid.hex}
        )

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('openstacktenant-sgp-list')


class BackupScheduleFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.BackupSchedule

    instance = factory.SubFactory(InstanceFactory)
    state = models.BackupSchedule.States.OK
    service_project_link = factory.SelfAttribute('instance.service_project_link')
    retention_time = 10
    is_active = True
    maximal_number_of_resources = 3
    schedule = '0 * * * *'

    @classmethod
    def get_url(cls, schedule, action=None):
        if schedule is None:
            schedule = BackupScheduleFactory()
        url = 'http://testserver' + reverse(
            'openstacktenant-backup-schedule-detail', kwargs={'uuid': schedule.uuid.hex}
        )
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('openstacktenant-backup-schedule-list')


class BackupFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Backup

    service_project_link = factory.SubFactory(OpenStackTenantServiceProjectLinkFactory)
    backup_schedule = factory.SubFactory(BackupScheduleFactory)
    instance = factory.LazyAttribute(lambda b: b.backup_schedule.instance)
    state = models.Backup.States.OK
    kept_until = fuzzy.FuzzyDateTime(timezone.datetime(2017, 6, 6, tzinfo=pytz.UTC))

    @classmethod
    def get_url(cls, backup=None, action=None):
        if backup is None:
            backup = BackupFactory()
        url = 'http://testserver' + reverse(
            'openstacktenant-backup-detail', kwargs={'uuid': backup.uuid.hex}
        )
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('openstacktenant-backup-list')


class SnapshotFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Snapshot

    size = 1024
    service_project_link = factory.SubFactory(OpenStackTenantServiceProjectLinkFactory)
    source_volume = factory.SubFactory(VolumeFactory)
    name = factory.Sequence(lambda n: 'Snapshot #%s' % n)
    state = models.Snapshot.States.OK

    @classmethod
    def get_url(cls, snapshot, action=None):
        if snapshot is None:
            snapshot = SnapshotFactory()
        url = 'http://testserver' + reverse(
            'openstacktenant-snapshot-detail', kwargs={'uuid': snapshot.uuid.hex}
        )
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls, action=None):
        url = 'http://testserver' + reverse('openstacktenant-snapshot-list')
        return url if action is None else url + action + '/'


class SnapshotRestorationFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.SnapshotRestoration

    snapshot = factory.SubFactory(SnapshotFactory)
    volume = factory.SubFactory(VolumeFactory)


class SnapshotScheduleFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.SnapshotSchedule

    source_volume = factory.SubFactory(VolumeFactory)
    state = models.SnapshotSchedule.States.OK
    service_project_link = factory.SelfAttribute('source_volume.service_project_link')
    retention_time = 10
    is_active = True
    maximal_number_of_resources = 3
    schedule = '0 * * * *'

    @classmethod
    def get_url(cls, schedule, action=None):
        if schedule is None:
            schedule = SnapshotScheduleFactory()
        url = 'http://testserver' + reverse(
            'openstacktenant-snapshot-schedule-detail',
            kwargs={'uuid': schedule.uuid.hex},
        )
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('openstacktenant-snapshot-schedule-list')


class NetworkFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Network

    name = factory.Sequence(lambda n: 'network%s' % n)
    backend_id = factory.Sequence(lambda n: 'backend_id_%s' % n)
    settings = factory.SubFactory(OpenStackTenantServiceSettingsFactory)
    is_external = False
    type = factory.Sequence(lambda n: 'network type%s' % n)
    segmentation_id = 8


class SubNetFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.SubNet

    name = factory.Sequence(lambda n: 'subnet%s' % n)
    backend_id = factory.Sequence(lambda n: 'backend_id_%s' % n)
    settings = factory.SubFactory(OpenStackTenantServiceSettingsFactory)
    network = factory.SubFactory(NetworkFactory)

    @classmethod
    def get_url(cls, subnet=None):
        if subnet is None:
            subnet = SubNetFactory()
        return 'http://testserver' + reverse(
            'openstacktenant-subnet-detail', kwargs={'uuid': subnet.uuid.hex}
        )

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('openstacktenant-subnet-list')


class InternalIPFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.InternalIP

    backend_id = factory.Sequence(lambda n: 'backend_id_%s' % n)
    instance = factory.SubFactory(InstanceFactory)
    subnet = factory.SubFactory(SubNetFactory)
    settings = factory.SelfAttribute('subnet.settings')


class VolumeTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.VolumeType

    name = factory.Sequence(lambda n: 'volume_type_%s' % n)
    backend_id = factory.Sequence(lambda n: 'backend_id_%s' % n)
    settings = factory.SubFactory(OpenStackTenantServiceSettingsFactory)

    @classmethod
    def get_url(cls, volume_type=None):
        if volume_type is None:
            volume_type = VolumeTypeFactory()
        return 'http://testserver' + reverse(
            'openstacktenant-volume-type-detail', kwargs={'uuid': volume_type.uuid.hex}
        )

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('openstacktenant-volume-type-list')


class VolumeAvailabilityZoneFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.VolumeAvailabilityZone

    name = factory.Sequence(lambda n: 'volume_availability_zone_%s' % n)
    settings = factory.SubFactory(OpenStackTenantServiceSettingsFactory)

    @classmethod
    def get_url(cls, volume_availability_zone=None):
        if volume_availability_zone is None:
            volume_availability_zone = VolumeAvailabilityZoneFactory()
        return 'http://testserver' + reverse(
            'openstacktenant-volume-availability-zone-detail',
            kwargs={'uuid': volume_availability_zone.uuid.hex},
        )

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse(
            'openstacktenant-volume-availability-zone-list'
        )
