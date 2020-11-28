from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from waldur_core.core import models as core_models
from waldur_core.core.fields import JSONField
from waldur_core.structure import models as structure_models


class BaseSecurityGroupRule(core_models.DescribableMixin, models.Model):
    TCP = 'tcp'
    UDP = 'udp'
    ICMP = 'icmp'

    PROTOCOLS = (
        (TCP, 'tcp'),
        (UDP, 'udp'),
        (ICMP, 'icmp'),
    )

    INGRESS = 'ingress'
    EGRESS = 'egress'

    DIRECTIONS = (
        (INGRESS, 'ingress'),
        (EGRESS, 'egress'),
    )

    IPv4 = 'IPv4'
    IPv6 = 'IPv6'

    ETHER_TYPES = (
        (IPv4, 'IPv4'),
        (IPv6, 'IPv6'),
    )

    # Empty string represents any protocol
    protocol = models.CharField(max_length=4, blank=True, choices=PROTOCOLS)
    from_port = models.IntegerField(validators=[MaxValueValidator(65535)], null=True)
    to_port = models.IntegerField(validators=[MaxValueValidator(65535)], null=True)
    cidr = models.CharField(max_length=32, blank=True, null=True)
    direction = models.CharField(max_length=8, default=INGRESS, choices=DIRECTIONS)
    ethertype = models.CharField(max_length=8, default=IPv4, choices=ETHER_TYPES)

    backend_id = models.CharField(max_length=128, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return '%s (%s): %s (%s -> %s)' % (
            self.security_group,
            self.protocol,
            self.cidr,
            self.from_port,
            self.to_port,
        )


class Port(core_models.BackendModelMixin, models.Model):
    # TODO: Use dedicated field: https://github.com/django-macaddress/django-macaddress
    mac_address = models.CharField(max_length=32, blank=True)
    ip4_address = models.GenericIPAddressField(null=True, blank=True, protocol='IPv4')
    ip6_address = models.GenericIPAddressField(null=True, blank=True, protocol='IPv6')
    backend_id = models.CharField(max_length=255, blank=True)

    allowed_address_pairs = JSONField(
        default=list,
        help_text=_(
            'A server can send a packet with source address which matches one of the specified allowed address pairs.'
        ),
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.ip4_address or self.ip6_address or 'Not initialized'

    @classmethod
    def get_backend_fields(cls):
        return super(Port, cls).get_backend_fields() + (
            'ip4_address',
            'ip6_address',
            'mac_address',
            'allowed_address_pairs',
        )


class BaseImage(structure_models.ServiceProperty):
    min_disk = models.PositiveIntegerField(
        default=0, help_text=_('Minimum disk size in MiB')
    )
    min_ram = models.PositiveIntegerField(
        default=0, help_text=_('Minimum memory size in MiB')
    )

    class Meta(structure_models.ServiceProperty.Meta):
        abstract = True

    @classmethod
    def get_backend_fields(cls):
        return super(BaseImage, cls).get_backend_fields() + ('min_disk', 'min_ram')


class BaseVolumeType(core_models.DescribableMixin, structure_models.ServiceProperty):
    class Meta:
        unique_together = ('settings', 'backend_id')
        abstract = True

    def __str__(self):
        return self.name


class BaseSubNet(models.Model):
    class Meta:
        abstract = True

    cidr = models.CharField(max_length=32, blank=True)
    gateway_ip = models.GenericIPAddressField(protocol='IPv4', null=True)
    allocation_pools = JSONField(default=dict)
    ip_version = models.SmallIntegerField(default=4)
    enable_dhcp = models.BooleanField(default=True)
    dns_nameservers = JSONField(
        default=list,
        help_text=_('List of DNS name servers associated with the subnet.'),
    )
    is_connected = models.BooleanField(
        default=True, help_text=_('Is subnet connected to the default tenant router.')
    )
