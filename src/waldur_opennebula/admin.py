from django.contrib import admin
from .models import OpenNebulaTenant, OpenNebulaVirtualMachine, OpenNebulaNetwork, OpenNebulaVolume


@admin.register(OpenNebulaTenant)
class OpenNebulaTenantAdmin(admin.ModelAdmin):
    list_display = ("name", "backend_id", "service_settings", "project", "created", "modified")
    search_fields = ("name", "backend_id")


@admin.register(OpenNebulaVirtualMachine)
class OpenNebulaVirtualMachineAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "project", "service_settings", "backend_id", "cpu", "ram", "disk", "created", "modified")
    search_fields = ("name", "backend_id")


@admin.register(OpenNebulaNetwork)
class OpenNebulaNetworkAdmin(admin.ModelAdmin):
    list_display = ("name", "backend_id", "tenant", "service_settings", "created", "modified")
    search_fields = ("name", "backend_id")


@admin.register(OpenNebulaVolume)
class OpenNebulaVolumeAdmin(admin.ModelAdmin):
    list_display = ("name", "backend_id", "tenant", "service_settings", "size", "created", "modified")
    search_fields = ("name", "backend_id") 