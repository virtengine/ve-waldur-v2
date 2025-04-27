from .views import (
    OpenNebulaTenantViewSet,
    OpenNebulaVirtualMachineViewSet,
    OpenNebulaNetworkViewSet,
    OpenNebulaVolumeViewSet,
    OpenNebulaScheduledActionViewSet,
    OpenNebulaTemplatesViewSet,
    OpenNebulaImagesViewSet,
    OpenNebulaQuotaView
)
from django.urls import path


def register_in(router):
    router.register(r'opennebula-tenants', OpenNebulaTenantViewSet, basename='opennebula-tenant')
    router.register(r'opennebula-vms', OpenNebulaVirtualMachineViewSet, basename='opennebula-vm')
    router.register(r'opennebula-networks', OpenNebulaNetworkViewSet, basename='opennebula-network')
    router.register(r'opennebula-volumes', OpenNebulaVolumeViewSet, basename='opennebula-volume')
    router.register(r'opennebula-scheduled-actions', OpenNebulaScheduledActionViewSet, basename='opennebula-scheduled-action')
    router.register(r'opennebula-templates', OpenNebulaTemplatesViewSet, basename='opennebula-template')
    router.register(r'opennebula-images', OpenNebulaImagesViewSet, basename='opennebula-image')

urlpatterns = [
    # Quota view - the only one that needs a special URL pattern
    path('tenants/<int:tenant_pk>/quota/', OpenNebulaQuotaView.as_view(), name='opennebula-tenant-quota'),
]