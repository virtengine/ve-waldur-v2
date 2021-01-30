import django_filters

from waldur_core.structure import filters as structure_filters

from . import models


## Class to filter EC2 instances by images
class ImageFilter(structure_filters.BaseServicePropertyFilter):
    class Meta:
        model = models.Image
        fields = structure_filters.BaseServicePropertyFilter.Meta.fields + ('region',)

    region = django_filters.UUIDFilter(field_name='region__uuid')


## Class to filter EC2 instances by sizes
class SizeFilter(structure_filters.BaseServicePropertyFilter):
    class Meta:
        model = models.Size
        fields = structure_filters.BaseServicePropertyFilter.Meta.fields + ('region',)

    region = django_filters.UUIDFilter(field_name='regions__uuid')


## Class to filter EC2 instances by regions 
class RegionFilter(structure_filters.BaseServicePropertyFilter):
    class Meta(structure_filters.BaseServicePropertyFilter.Meta):
        model = models.Region


## Class to filet EC2 instances
class InstanceFilter(structure_filters.BaseResourceFilter):
    external_ip = django_filters.CharFilter(field_name='public_ips')

    class Meta(structure_filters.BaseResourceFilter.Meta):
        model = models.Instance
