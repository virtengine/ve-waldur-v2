from .views import OpenNebulaTenantViewSet, OpenNebulaVirtualMachineViewSet, OpenNebulaNetworkViewSet, OpenNebulaVolumeViewSet
from django.urls import path
from .views import (
    OpenNebulaTemplateListView,
    OpenNebulaImageListView,
    OpenNebulaNetworkListView,
    OpenNebulaVMCreateView,
    OpenNebulaVMMigrateView,
    OpenNebulaDiskAttachView,
    OpenNebulaDiskResizeView,
    OpenNebulaDiskSaveAsView,
    OpenNebulaFloatingIPAssignView,
    OpenNebulaFloatingIPReleaseView,
    OpenNebulaMarketplaceOfferingListView,
)


def register_in(router):
    router.register(r'opennebula-tenants', OpenNebulaTenantViewSet, basename='opennebula-tenant')
    router.register(r'opennebula-vms', OpenNebulaVirtualMachineViewSet, basename='opennebula-vm')
    router.register(r'opennebula-networks', OpenNebulaNetworkViewSet, basename='opennebula-network')
    router.register(r'opennebula-volumes', OpenNebulaVolumeViewSet, basename='opennebula-volume')

urlpatterns = [
    path('templates/', OpenNebulaTemplateListView.as_view(), name='opennebula-template-list'),
    path('images/', OpenNebulaImageListView.as_view(), name='opennebula-image-list'),
    path('networks/', OpenNebulaNetworkListView.as_view(), name='opennebula-network-list'),
    path('vms/create/', OpenNebulaVMCreateView.as_view(), name='opennebula-vm-create'),
    path('vms/migrate/', OpenNebulaVMMigrateView.as_view(), name='opennebula-vm-migrate'),
    path('vms/attach_disk/', OpenNebulaDiskAttachView.as_view(), name='opennebula-vm-attach-disk'),
    path('vms/resize_disk/', OpenNebulaDiskResizeView.as_view(), name='opennebula-vm-resize-disk'),
    path('vms/save_disk_as_image/', OpenNebulaDiskSaveAsView.as_view(), name='opennebula-vm-save-disk-as-image'),
    path('floating_ips/assign/', OpenNebulaFloatingIPAssignView.as_view(), name='opennebula-floatingip-assign'),
    path('floating_ips/release/', OpenNebulaFloatingIPReleaseView.as_view(), name='opennebula-floatingip-release'),
    path('marketplace/offerings/', OpenNebulaMarketplaceOfferingListView.as_view(), name='opennebula-marketplace-offering-list'),
] 