import django_filters

from waldur_core.core import filters as core_filters
from waldur_core.structure import filters as structure_filters

from . import models


class SlurmServiceProjectLinkFilter(structure_filters.BaseServiceProjectLinkFilter):
    service = core_filters.URLFilter(
        view_name='slurm-detail', field_name='service__uuid'
    )

    class Meta(structure_filters.BaseServiceProjectLinkFilter.Meta):
        model = models.SlurmServiceProjectLink


class AllocationFilter(structure_filters.BaseResourceFilter):
    class Meta(structure_filters.BaseResourceFilter.Meta):
        model = models.Allocation
        fields = structure_filters.BaseResourceFilter.Meta.fields + ('is_active',)


class AllocationUsageFilter(django_filters.FilterSet):
    allocation = core_filters.URLFilter(
        view_name='slurm-allocation-detail', field_name='allocation__uuid'
    )
    allocation_uuid = django_filters.UUIDFilter(field_name='allocation__uuid')

    class Meta:
        model = models.AllocationUsage
        fields = ('year', 'month')


class AllocationUserUsageFilter(django_filters.FilterSet):
    allocation = core_filters.URLFilter(
        view_name='slurm-allocation-detail',
        field_name='allocation_usage__allocation__uuid',
    )
    allocation_uuid = django_filters.UUIDFilter(
        field_name='allocation_usage__allocation__uuid'
    )

    allocation_usage = core_filters.URLFilter(
        view_name='slurm-allocation-usage-detail', field_name='allocation_usage__uuid',
    )
    allocation_usage_uuid = django_filters.UUIDFilter(
        field_name='allocation_usage__uuid'
    )

    user = core_filters.URLFilter(view_name='user-detail', field_name='user__uuid')
    user_uuid = django_filters.UUIDFilter(field_name='user__uuid')
