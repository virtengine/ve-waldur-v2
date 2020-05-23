import factory
from django.urls import reverse
from factory import fuzzy

from waldur_core.structure.tests import factories as structure_factories

from .. import models


class DigitalOceanServiceFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.DigitalOceanService

    settings = factory.SubFactory(
        structure_factories.ServiceSettingsFactory, type='DigitalOcean'
    )
    customer = factory.SubFactory(structure_factories.CustomerFactory)

    @classmethod
    def get_url(cls, service=None, action=None):
        if service is None:
            service = DigitalOceanServiceFactory()
        url = 'http://testserver' + reverse(
            'digitalocean-detail', kwargs={'uuid': service.uuid.hex}
        )
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('digitalocean-list')


class DigitalOceanServiceProjectLinkFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.DigitalOceanServiceProjectLink

    service = factory.SubFactory(DigitalOceanServiceFactory)
    project = factory.SubFactory(structure_factories.ProjectFactory)

    @classmethod
    def get_url(cls, link=None):
        if link is None:
            link = DigitalOceanServiceProjectLinkFactory()
        return 'http://testserver' + reverse(
            'digitalocean-spl-detail', kwargs={'pk': link.id}
        )


class RegionFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Region

    name = factory.Sequence(lambda n: 'region%s' % n)
    backend_id = factory.Sequence(lambda n: 'region-id%s' % n)

    @classmethod
    def get_url(cls, region=None):
        if region is None:
            region = RegionFactory()
        return 'http://testserver' + reverse(
            'digitalocean-region-detail', kwargs={'uuid': region.uuid.hex}
        )


class ImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Image

    name = factory.Sequence(lambda n: 'image%s' % n)
    backend_id = factory.Sequence(lambda n: 'image-id%s' % n)

    @classmethod
    def get_url(cls, image=None):
        if image is None:
            image = ImageFactory()
        return 'http://testserver' + reverse(
            'digitalocean-image-detail', kwargs={'uuid': image.uuid.hex}
        )

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('digitalocean-image-list')


class SizeFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Size

    name = factory.Sequence(lambda n: 'size%s' % n)
    backend_id = factory.Sequence(lambda n: 'size-id%s' % n)

    cores = fuzzy.FuzzyInteger(1, 8, step=2)
    ram = fuzzy.FuzzyInteger(1024, 10240, step=1024)
    disk = fuzzy.FuzzyInteger(1024, 102400, step=1024)
    transfer = fuzzy.FuzzyInteger(10240, 102400, step=10240)
    price = fuzzy.FuzzyDecimal(0.5, 5, precision=2)

    @classmethod
    def get_url(cls, size=None):
        if size is None:
            size = SizeFactory()
        return 'http://testserver' + reverse(
            'digitalocean-size-detail', kwargs={'uuid': size.uuid.hex}
        )


class DropletFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Droplet

    name = factory.Sequence(lambda n: 'droplet%s' % n)
    backend_id = factory.Sequence(lambda n: 'droplet-id%s' % n)
    service_project_link = factory.SubFactory(DigitalOceanServiceProjectLinkFactory)

    state = models.Droplet.States.OK
    runtime_state = models.Droplet.RuntimeStates.ONLINE
    cores = fuzzy.FuzzyInteger(1, 8, step=2)
    ram = fuzzy.FuzzyInteger(1024, 10240, step=1024)
    disk = fuzzy.FuzzyInteger(1024, 102400, step=1024)
    transfer = fuzzy.FuzzyInteger(10240, 102400, step=10240)

    @classmethod
    def get_url(cls, droplet=None, action=None):
        if droplet is None:
            droplet = DropletFactory()
        url = 'http://testserver' + reverse(
            'digitalocean-droplet-detail', kwargs={'uuid': droplet.uuid.hex}
        )
        return url if action is None else url + action + '/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('digitalocean-droplet-list')
