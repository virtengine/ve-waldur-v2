from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter

from .views import (
    OpenNebulaBackupCreateView,
    OpenNebulaBackupListView,
    OpenNebulaDiskAttachView,
    OpenNebulaDiskResizeView,
    OpenNebulaDiskSaveAsView,
    OpenNebulaFloatingIPAssignView,
    OpenNebulaFloatingIPReleaseView,
    OpenNebulaImageListView,
    OpenNebulaMarketplaceOfferingListView,
    OpenNebulaNetworkViewSet,
    OpenNebulaPingView,
    OpenNebulaQuotaView,
    OpenNebulaRestoreBackupView,
    OpenNebulaScheduledActionViewSet,
    OpenNebulaTemplateListView,
    OpenNebulaTenantViewSet,
    OpenNebulaVirtualMachineViewSet,
    OpenNebulaVMCreateView,
    OpenNebulaVMListSnapshotsView,
    OpenNebulaVMMigrateView,
    OpenNebulaVMMonitoringView,
    OpenNebulaVMPoolMonitoringView,
    OpenNebulaVMSnapshotView,
    OpenNebulaVolumeViewSet,
)

router = DefaultRouter()
alias_router = SimpleRouter()


def register_in(router_instance):
    router_instance.register(
        r"opennebula-tenants", OpenNebulaTenantViewSet, basename="opennebula-tenant"
    )
    router_instance.register(
        r"opennebula-vms", OpenNebulaVirtualMachineViewSet, basename="opennebula-vm"
    )
    router_instance.register(
        r"opennebula-networks", OpenNebulaNetworkViewSet, basename="opennebula-network"
    )
    router_instance.register(
        r"opennebula-volumes", OpenNebulaVolumeViewSet, basename="opennebula-volume"
    )
    router_instance.register(
        r"opennebula-scheduled-actions",
        OpenNebulaScheduledActionViewSet,
        basename="opennebula-scheduled-action",
    )


def register_aliases(router_instance):
    router_instance.register(
        r"opennebula-tenants", OpenNebulaTenantViewSet, basename="opennebulatenant"
    )
    router_instance.register(
        r"opennebula-vms",
        OpenNebulaVirtualMachineViewSet,
        basename="opennebulavirtualmachine",
    )
    router_instance.register(
        r"opennebula-networks", OpenNebulaNetworkViewSet, basename="opennebulanetwork"
    )
    router_instance.register(
        r"opennebula-volumes", OpenNebulaVolumeViewSet, basename="opennebulavolume"
    )
    router_instance.register(
        r"opennebula-scheduled-actions",
        OpenNebulaScheduledActionViewSet,
        basename="opennebulascheduledaction",
    )


register_in(router)
register_aliases(alias_router)


urlpatterns = [
    path("", include(router.urls)),
    path("", include(alias_router.urls)),
    path(
        "opennebula/templates/",
        OpenNebulaTemplateListView.as_view(),
        name="opennebula-template-list",
    ),
    path(
        "opennebula/images/",
        OpenNebulaImageListView.as_view(),
        name="opennebula-image-list",
    ),
    path(
        "opennebula/vm/create/",
        OpenNebulaVMCreateView.as_view(),
        name="opennebula-vm-create",
    ),
    path(
        "opennebula/vm/migrate/",
        OpenNebulaVMMigrateView.as_view(),
        name="opennebula-vm-migrate",
    ),
    path(
        "opennebula/vm/attach-disk/",
        OpenNebulaDiskAttachView.as_view(),
        name="opennebula-vm-attach-disk",
    ),
    path(
        "opennebula/vm/resize-disk/",
        OpenNebulaDiskResizeView.as_view(),
        name="opennebula-vm-resize-disk",
    ),
    path(
        "opennebula/vm/save-disk-as-image/",
        OpenNebulaDiskSaveAsView.as_view(),
        name="opennebula-vm-save-disk-as-image",
    ),
    path(
        "opennebula/vm/snapshot/",
        OpenNebulaVMSnapshotView.as_view(),
        name="opennebulavmsnapshotview",
    ),
    path(
        "opennebula/vm/snapshots/",
        OpenNebulaVMListSnapshotsView.as_view(),
        name="opennebulavmlistsnapshotsview",
    ),
    path(
        "opennebula/vm/backups/create/",
        OpenNebulaBackupCreateView.as_view(),
        name="opennebulabackupcreateview",
    ),
    path(
        "opennebula/vm/backups/",
        OpenNebulaBackupListView.as_view(),
        name="opennebulabackuplistview",
    ),
    path(
        "opennebula/vm/backups/restore/",
        OpenNebulaRestoreBackupView.as_view(),
        name="opennebularestorebackupview",
    ),
    path(
        "opennebula/floating-ips/assign/",
        OpenNebulaFloatingIPAssignView.as_view(),
        name="opennebula-floatingip-assign",
    ),
    path(
        "opennebula/floating-ips/release/",
        OpenNebulaFloatingIPReleaseView.as_view(),
        name="opennebula-floatingip-release",
    ),
    path(
        "opennebula/marketplace/offerings/",
        OpenNebulaMarketplaceOfferingListView.as_view(),
        name="opennebula-marketplace-offering-list",
    ),
    path(
        "opennebula/vm/<int:pk>/monitoring/",
        OpenNebulaVMMonitoringView.as_view(),
        name="opennebula-vm-monitoring",
    ),
    path(
        "opennebula/vm/pool-monitoring/",
        OpenNebulaVMPoolMonitoringView.as_view(),
        name="opennebula-vm-pool-monitoring",
    ),
    path(
        "opennebula/tenants/<int:tenant_pk>/quota/",
        OpenNebulaQuotaView.as_view(),
        name="opennebula-tenant-quota",
    ),
    path(
        "opennebula/ping/",
        OpenNebulaPingView.as_view(),
        name="opennebula-api-ping",
    ),
]
