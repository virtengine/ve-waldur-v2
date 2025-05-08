from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OpenNebulaTenantViewSet,
    OpenNebulaVirtualMachineViewSet,
    OpenNebulaNetworkViewSet,
    OpenNebulaVolumeViewSet,
    OpenNebulaScheduledActionViewSet,
)

router = DefaultRouter()

def register_in(router):
    router.register(r'opennebula-tenants', OpenNebulaTenantViewSet, basename='opennebula-tenant')
    router.register(r'opennebula-vms', OpenNebulaVirtualMachineViewSet, basename='opennebula-vm')
    router.register(r'opennebula-networks', OpenNebulaNetworkViewSet, basename='opennebula-network')
    router.register(r'opennebula-volumes', OpenNebulaVolumeViewSet, basename='opennebula-volume')
    router.register(r'opennebula-scheduled-actions', OpenNebulaScheduledActionViewSet, basename='opennebula-scheduled-action')


urlpatterns = []