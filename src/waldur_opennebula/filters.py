import django_filters
from .models import OpenNebulaTenant, OpenNebulaVirtualMachine


class OpenNebulaTenantFilter(django_filters.FilterSet):
    class Meta:
        model = OpenNebulaTenant
        fields = ["name", "backend_id", "service_settings"]


class OpenNebulaVirtualMachineFilter(django_filters.FilterSet):
    class Meta:
        model = OpenNebulaVirtualMachine
        fields = ["tenant", "project", "service_settings", "backend_id"] 