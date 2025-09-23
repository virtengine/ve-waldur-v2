from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    OpenNebulaFloatingIPAssignView,
    OpenNebulaFloatingIPReleaseView,
    OpenNebulaNetworkViewSet,
    OpenNebulaScheduledActionViewSet,
    OpenNebulaTenantViewSet,
    OpenNebulaVirtualMachineViewSet,
    OpenNebulaVolumeViewSet,
)

router = DefaultRouter()


def register_in(router):
    router.register(
        r"opennebula-tenants", OpenNebulaTenantViewSet, basename="opennebula-tenant"
    )
    router.register(
        r"opennebula-vms", OpenNebulaVirtualMachineViewSet, basename="opennebula-vm"
    )
    router.register(
        r"opennebula-networks", OpenNebulaNetworkViewSet, basename="opennebula-network"
    )
    router.register(
        r"opennebula-volumes", OpenNebulaVolumeViewSet, basename="opennebula-volume"
    )
    router.register(
        r"opennebula-scheduled-actions",
        OpenNebulaScheduledActionViewSet,
        basename="opennebula-scheduled-action",
    )


urlpatterns = [
    path(
        "opennebula-floatingips/assign/",
        OpenNebulaFloatingIPAssignView.as_view(),
        name="opennebula-floatingip-assign",
    ),
    path(
        "opennebula-floatingips/release/",
        OpenNebulaFloatingIPReleaseView.as_view(),
        name="opennebula-floatingip-release",
    ),
]
