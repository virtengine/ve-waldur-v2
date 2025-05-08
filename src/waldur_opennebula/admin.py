from django.contrib import admin
from .models import OpenNebulaScheduledAction, OpenNebulaTenant, OpenNebulaVirtualMachine, OpenNebulaNetwork, OpenNebulaVolume
from waldur_core.structure import admin as structure_admin


@admin.register(OpenNebulaTenant)
class OpenNebulaTenantAdmin(structure_admin.ResourceAdmin):
    list_display = ('name', 'state', 'backend_id')
    search_fields = ('name', 'backend_id')
    list_filter = ('state',)

@admin.register(OpenNebulaVirtualMachine)
class OpenNebulaVirtualMachineAdmin(structure_admin.ResourceAdmin):
    list_display = ('name', 'state', 'backend_id', 'cpu', 'ram')
    search_fields = ('name', 'backend_id')
    list_filter = ('state', 'cpu', 'ram')

@admin.register(OpenNebulaNetwork)
class OpenNebulaNetworkAdmin(structure_admin.ResourceAdmin):
    list_display = ('name', 'state', 'backend_id')
    search_fields = ('name', 'backend_id')
    list_filter = ('state',)

@admin.register(OpenNebulaVolume)
class OpenNebulaVolumeAdmin(structure_admin.ResourceAdmin):
    list_display = ('name', 'state', 'backend_id', 'size')
    search_fields = ('name', 'backend_id')
    list_filter = ('state', 'size')

@admin.register(OpenNebulaScheduledAction)
class OpenNebulaScheduledActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'vm', 'next_run', 'action_type', 'enabled', 'last_run')
    list_filter = ('action_type', 'enabled')
    search_fields = ('id', 'vm__name')