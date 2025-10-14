from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from waldur_core.structure.models import ServiceSettings

from .backend import OpenNebulaBackend
from .client import OpenNebulaClient
from .executors import (
    TenantPullExecutor,
    VirtualMachineCreateExecutor,
    VirtualMachineDeleteExecutor,
    VirtualMachineRebootExecutor,
    VirtualMachineStartExecutor,
    VirtualMachineStopExecutor,
)
from .models import (
    OpenNebulaNetwork,
    OpenNebulaScheduledAction,
    OpenNebulaTenant,
    OpenNebulaVirtualMachine,
    OpenNebulaVolume,
)
from .serializers import (
    OpenNebulaBackupCreateSerializer,
    OpenNebulaBackupListSerializer,
    OpenNebulaDiskAttachSerializer,
    OpenNebulaDiskResizeSerializer,
    OpenNebulaDiskSaveAsSerializer,
    OpenNebulaMarketplaceOfferingSerializer,
    OpenNebulaNetworkAttachSerializer,
    OpenNebulaNetworkListSerializer,
    OpenNebulaNetworkReleaseSerializer,
    OpenNebulaNetworkSerializer,
    OpenNebulaNetworkUpdateSerializer,
    OpenNebulaQuotaSerializer,
    OpenNebulaRestoreBackupSerializer,
    OpenNebulaScheduledActionSerializer,
    OpenNebulaTenantCreateSerializer,
    OpenNebulaTenantSerializer,
    OpenNebulaVirtualMachineSerializer,
    OpenNebulaVMCreateSerializer,
    OpenNebulaVMListSnapshotsSerializer,
    OpenNebulaVMMigrateSerializer,
    OpenNebulaVMMonitoringSerializer,
    OpenNebulaVMSnapshotSerializer,
    OpenNebulaVolumeSerializer,
)
from .tasks import (
    attach_disk_task,
    create_backup_task,
    create_vm_snapshot_task,
    create_vm_task,
    migrate_vm_task,
    resize_disk_task,
    restore_backup_task,
    save_disk_as_image_task,
)


class OpenNebulaTenantViewSet(viewsets.ModelViewSet):
    queryset = OpenNebulaTenant.objects.all()
    serializer_class = OpenNebulaTenantSerializer

    def create(self, request, *args, **kwargs):
        serializer = OpenNebulaTenantCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        tenant = serializer.save()
        backend = OpenNebulaBackend(tenant.service_settings)
        backend.create_tenant(tenant)
        response_serializer = OpenNebulaTenantSerializer(
            tenant, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"])
    def delete_tenant(self, request, pk=None):
        tenant = self.get_object()
        backend = OpenNebulaBackend(tenant.service_settings)
        backend.delete_tenant(tenant)
        return Response(
            {"detail": "Tenant deleted."}, status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=["post"])
    def pull(self, request):
        service_settings_id = request.data.get("service_settings_id")
        if not service_settings_id:
            return Response(
                {"detail": "service_settings_id required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        TenantPullExecutor.execute(service_settings_id)
        return Response({"detail": "Pull scheduled."}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def set_quotas(self, request, pk=None):
        tenant = self.get_object()
        quota_template = request.data.get("quota_template")
        if not quota_template:
            return Response(
                {"detail": "quota_template is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        backend = OpenNebulaBackend(tenant.service_settings)
        try:
            result = backend.set_tenant_quota(tenant, quota_template)
            return Response(
                {"detail": "Quota set.", "result": str(result)},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def pull_quotas(self, request, pk=None):
        tenant = self.get_object()
        backend = OpenNebulaBackend(tenant.service_settings)
        try:
            quotas = backend.get_tenant_quota(tenant)
            return Response({"quotas": str(quotas)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def create_network(self, request, pk=None):
        # This could be implemented if OpenNebula supports network creation per group/project
        return Response(
            {"detail": "Network creation for tenant is not implemented yet."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=True, methods=["post"])
    def create_floating_ip(self, request, pk=None):
        # OpenNebula does not have a direct floating IP concept like OpenStack
        return Response(
            {"detail": "Floating IPs are not supported by OpenNebula."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=True, methods=["post"])
    def pull_floating_ips(self, request, pk=None):
        # OpenNebula does not have a direct floating IP concept like OpenStack
        return Response(
            {"detail": "Floating IPs are not supported by OpenNebula."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=True, methods=["post"])
    def pull_security_groups(self, request, pk=None):
        # OpenNebula does not have security groups like OpenStack
        return Response(
            {"detail": "Security groups are not supported by OpenNebula."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=True, methods=["post"])
    def pull_server_groups(self, request, pk=None):
        # OpenNebula does not have server groups like OpenStack
        return Response(
            {"detail": "Server groups are not supported by OpenNebula."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=True, methods=["post"])
    def create_server_group(self, request, pk=None):
        # OpenNebula does not have server groups like OpenStack
        return Response(
            {"detail": "Server groups are not supported by OpenNebula."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=True, methods=["get"])
    def backend_instances(self, request, pk=None):
        tenant = self.get_object()
        backend = OpenNebulaBackend(tenant.service_settings)
        try:
            vms = backend.pull_vms(tenant=tenant)
            data = OpenNebulaVirtualMachineSerializer(vms, many=True).data
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def backend_vms(self, request, pk=None):
        tenant = self.get_object()
        backend = OpenNebulaBackend(tenant.service_settings)
        try:
            vms = backend.pull_vms(tenant=tenant)
            data = OpenNebulaVirtualMachineSerializer(vms, many=True).data
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def backend_volumes(self, request, pk=None):
        tenant = self.get_object()
        backend = OpenNebulaBackend(tenant.service_settings)
        try:
            volumes = backend.pull_volumes(tenant=tenant)
            data = OpenNebulaVolumeSerializer(volumes, many=True).data
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def backend_networks(self, request, pk=None):
        tenant = self.get_object()
        backend = OpenNebulaBackend(tenant.service_settings)
        try:
            networks = backend.pull_networks(tenant=tenant)
            data = OpenNebulaNetworkSerializer(networks, many=True).data
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OpenNebulaVirtualMachineViewSet(viewsets.ModelViewSet):
    queryset = OpenNebulaVirtualMachine.objects.all()
    serializer_class = OpenNebulaVirtualMachineSerializer

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        vm = self.get_object()
        VirtualMachineStartExecutor.execute(vm)
        return Response({"detail": "Start scheduled."}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def reboot(self, request, pk=None):
        vm = self.get_object()
        VirtualMachineRebootExecutor.execute(vm)
        return Response({"detail": "Start scheduled."}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        vm = self.get_object()
        VirtualMachineStopExecutor.execute(vm)
        return Response({"detail": "Stop scheduled."}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def delete_vm(self, request, pk=None):
        vm = self.get_object()
        VirtualMachineDeleteExecutor.execute(vm)
        return Response(
            {"detail": "Delete scheduled."}, status=status.HTTP_202_ACCEPTED
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        VirtualMachineCreateExecutor.execute(instance)
        return Response(
            self.get_serializer(instance).data, status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=["post"])
    def restart(self, request, pk=None):
        vm = self.get_object()
        backend = OpenNebulaBackend(vm.service_settings)
        try:
            backend.reboot_vm(vm)
            return Response(
                {"detail": "Restart scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def resize(self, request, pk=None):
        vm = self.get_object()
        cpu = request.data.get("cpu")
        ram = request.data.get("ram")
        backend = OpenNebulaBackend(vm.service_settings)
        try:
            backend.resize_vm(vm, cpu=cpu, ram=ram)
            return Response(
                {"detail": "Resize scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def attach_volume(self, request, pk=None):
        vm = self.get_object()
        volume_id = request.data.get("volume_id")
        if not volume_id:
            return Response(
                {"detail": "volume_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        from .models import OpenNebulaVolume

        try:
            volume = OpenNebulaVolume.objects.get(pk=volume_id)
        except OpenNebulaVolume.DoesNotExist:
            return Response(
                {"detail": "Volume not found."}, status=status.HTTP_404_NOT_FOUND
            )
        backend = OpenNebulaBackend(vm.service_settings)
        try:
            backend.attach_disk(vm, volume)
            return Response(
                {"detail": "Attach scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def detach_volume(self, request, pk=None):
        vm = self.get_object()
        disk_id = request.data.get("disk_id")
        if not disk_id:
            return Response(
                {"detail": "disk_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        backend = OpenNebulaBackend(vm.service_settings)
        try:
            backend.detach_disk(vm, disk_id)
            return Response(
                {"detail": "Detach scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def snapshot(self, request, pk=None):
        vm = self.get_object()
        name = request.data.get("name")
        if not name:
            return Response(
                {"detail": "name is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        backend = OpenNebulaBackend(vm.service_settings)
        try:
            backend.snapshot_vm(vm, name)
            return Response(
                {"detail": "Snapshot scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def restore_snapshot(self, request, pk=None):
        vm = self.get_object()
        snapshot_id = request.data.get("snapshot_id")
        if not snapshot_id:
            return Response(
                {"detail": "snapshot_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        backend = OpenNebulaBackend(vm.service_settings)
        try:
            backend.restore_vm_snapshot(vm, snapshot_id)
            return Response(
                {"detail": "Restore scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def console(self, request, pk=None):
        vm = self.get_object()
        backend = OpenNebulaBackend(vm.service_settings)
        try:
            console_info = backend.get_console(vm)
            return Response({"console": str(console_info)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def backup(self, request, pk=None):
        vm = self.get_object()
        ds_id = request.data.get("ds_id")
        reset = request.data.get("reset", False)
        if not ds_id:
            return Response(
                {"detail": "ds_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        backend = OpenNebulaBackend(vm.service_settings)
        try:
            backend.backup_vm(vm, ds_id, reset)
            return Response(
                {"detail": "Backup scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def backup_cancel(self, request, pk=None):
        vm = self.get_object()
        backend = OpenNebulaBackend(vm.service_settings)
        try:
            backend.backup_cancel(vm)
            return Response(
                {"detail": "Backup cancel scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        vm = self.get_object()
        backup_id = request.data.get("backup_id")
        in_place = request.data.get("in_place", True)
        if not backup_id:
            return Response(
                {"detail": "backup_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        backend = OpenNebulaBackend(vm.service_settings)
        try:
            backend.restore_vm(vm, backup_id, in_place)
            return Response(
                {"detail": "Restore scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        request=OpenNebulaVMCreateSerializer,
        responses={
            201: OpenApiResponse(description="VM created"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Create a new VM with the selected template, networks, and options.",
    )
    @action(detail=False, methods=["post"])
    def create_vm(self, request):
        serializer = OpenNebulaVMCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        settings = data["service_settings"]
        # Create DB record for VM in 'creating' state
        vm = OpenNebulaVirtualMachine.objects.create(
            name=data["name"],
            service_settings=settings,
            state="creating",
            # Add other required fields as needed (e.g., project, tenant)
        )
        # Schedule async Celery task
        create_vm_task(
            vm.pk,
            settings.pk,
            data["template_id"],
            data["name"],
            data["networks"],
            data.get("cpu"),
            data.get("ram"),
            data.get("disk"),
            data.get("ssh_key"),
            data.get("contextualization", False),
            data.get("extra", {}),
        )
        # Return VM object (with state) for polling
        return Response(
            OpenNebulaVirtualMachineSerializer(vm).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        request=OpenNebulaVMMigrateSerializer,
        responses={
            202: OpenApiResponse(description="Migration scheduled"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Migrate a VM to a target host/datastore.",
    )
    @action(detail=False, methods=["post"])
    def migrate(self, request):
        serializer = OpenNebulaVMMigrateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        migrate_vm_task(
            vm.pk,
            data["host_id"],
            data.get("live", True),
            data.get("enforce", False),
            data.get("ds_id"),
            data.get("migration_type", 0),
        )
        return Response(
            {"detail": "Migration scheduled."}, status=status.HTTP_202_ACCEPTED
        )

    @extend_schema(
        request=OpenNebulaDiskAttachSerializer,
        responses={
            202: OpenApiResponse(description="Disk attach scheduled"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Attach a disk/image to a VM.",
    )
    @action(detail=False, methods=["post"])
    def attach_disk(self, request):
        serializer = OpenNebulaDiskAttachSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        disk_template = {
            "IMAGE_ID": data["image_id"],
        }
        if data.get("size"):
            disk_template["SIZE"] = data["size"]
        if data.get("type"):
            disk_template["TYPE"] = data["type"]
        if data.get("target"):
            disk_template["TARGET"] = data["target"]
        attach_disk_task(vm.pk, disk_template)
        return Response(
            {"detail": "Disk attach scheduled."}, status=status.HTTP_202_ACCEPTED
        )

    @extend_schema(
        request=OpenNebulaDiskResizeSerializer,
        responses={
            202: OpenApiResponse(description="Disk resize scheduled"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Resize a disk attached to a VM.",
    )
    @action(detail=False, methods=["post"])
    def resize_disk(self, request):
        serializer = OpenNebulaDiskResizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        resize_disk_task(vm.pk, data["disk_id"], data["size"])
        return Response(
            {"detail": "Disk resize scheduled."}, status=status.HTTP_202_ACCEPTED
        )

    @extend_schema(
        request=OpenNebulaDiskSaveAsSerializer,
        responses={
            202: OpenApiResponse(description="Save disk as image scheduled"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Save a disk as a new image.",
    )
    @action(detail=False, methods=["post"])
    def save_disk_as_image(self, request):
        serializer = OpenNebulaDiskSaveAsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        save_disk_as_image_task(
            vm.pk,
            data["disk_id"],
            data["image_name"],
            data.get("image_type", ""),
            data.get("snapshot_id", -1),
        )
        return Response(
            {"detail": "Save as image scheduled."}, status=status.HTTP_202_ACCEPTED
        )

    @extend_schema(
        request=OpenNebulaVMSnapshotSerializer,
        responses={
            202: OpenApiResponse(description="Snapshot creation scheduled"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Create a snapshot for a VM.",
    )
    @action(detail=False, methods=["post"])
    def create_snapshot(self, request):
        serializer = OpenNebulaVMSnapshotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        create_vm_snapshot_task(data["vm"].pk, data["name"])
        return Response(
            {"detail": "Snapshot creation scheduled."}, status=status.HTTP_202_ACCEPTED
        )

    @extend_schema(
        request=OpenNebulaVMListSnapshotsSerializer,
        responses={
            200: OpenApiResponse(description="List of VM snapshots"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="List all snapshots for a VM.",
    )
    @action(detail=False, methods=["get"])
    def list_snapshots(self, request):
        serializer = OpenNebulaVMListSnapshotsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        try:
            backend = OpenNebulaBackend(vm.service_settings)
            snapshots = backend.list_snapshots(vm)
            return Response(snapshots, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        request=OpenNebulaBackupCreateSerializer,
        responses={
            202: OpenApiResponse(description="Backup creation scheduled"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Create a backup for a VM.",
    )
    @action(detail=False, methods=["post"])
    def create_backup(self, request):
        serializer = OpenNebulaBackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        create_backup_task(data["vm"].pk, data["name"], data.get("description", ""))
        return Response(
            {"detail": "Backup creation scheduled."}, status=status.HTTP_202_ACCEPTED
        )

    @extend_schema(
        request=OpenNebulaBackupListSerializer,
        responses={
            200: OpenApiResponse(description="List of VM backups"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="List all backups for a VM.",
    )
    @action(detail=False, methods=["get"])
    def list_backups(self, request):
        serializer = OpenNebulaBackupListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        try:
            backend = OpenNebulaBackend(vm.service_settings)
            backups = backend.list_backups(vm)
            return Response(backups, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        request=OpenNebulaRestoreBackupSerializer,
        responses={
            202: OpenApiResponse(description="Backup restore scheduled"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Restore a backup to a VM or as a new VM.",
    )
    @action(detail=False, methods=["post"])
    def restore_backup(self, request):
        serializer = OpenNebulaRestoreBackupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        restore_backup_task(
            data["backup_id"],
            data.get("vm").pk if data.get("vm") else None,
            data.get("in_place", True),
            data.get("new_vm_name", ""),
        )
        return Response(
            {"detail": "Backup restore scheduled."}, status=status.HTTP_202_ACCEPTED
        )

    @extend_schema(
        responses={200: OpenApiResponse(OpenNebulaVMMonitoringSerializer)},
        description="Get monitoring data for a VM.",
    )
    @action(detail=True, methods=["get"])
    def monitoring(self, request, pk=None):
        vm = self.get_object()
        backend = OpenNebulaBackend(vm.service_settings)
        data = backend.get_vm_monitoring(vm)
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={200: OpenApiResponse(OpenNebulaVMMonitoringSerializer(many=True))},
        description="Get monitoring data for all VMs.",
    )
    @action(detail=False, methods=["get"])
    def pool_monitoring(self, request):
        # Optionally filter by user/project
        backend = OpenNebulaBackend(
            ServiceSettings.objects.filter(type="OpenNebula").first()
        )
        data = backend.get_vmpool_monitoring()
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        request=OpenNebulaNetworkAttachSerializer,
        responses={
            200: OpenApiResponse(description="NIC attached"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Attach a network interface to a VM.",
    )
    @action(detail=False, methods=["post"])
    def attach_nic(self, request):
        serializer = OpenNebulaNetworkAttachSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            backend = OpenNebulaBackend(data["vm"].service_settings)
            result = backend.attach_nic(
                data["vm"],
                data["network_id"],
                ip=data.get("ip_address"),
                model=data.get("model"),
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        request=OpenNebulaNetworkReleaseSerializer,
        responses={
            200: OpenApiResponse(description="NIC detached"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Detach a network interface from a VM.",
    )
    @action(detail=False, methods=["post"])
    def detach_nic(self, request):
        serializer = OpenNebulaNetworkReleaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            backend = OpenNebulaBackend(data["vm"].service_settings)
            result = backend.detach_nic(data["vm"], data["nic_id"])
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        request=OpenNebulaNetworkUpdateSerializer,
        responses={
            200: OpenApiResponse(description="NIC updated"),
            400: OpenApiResponse(description="Validation error"),
        },
        description="Update a network interface configuration.",
    )
    @action(detail=False, methods=["post"])
    def update_nic(self, request):
        serializer = OpenNebulaNetworkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            backend = OpenNebulaBackend(data["vm"].service_settings)

            # Extract kwargs from the validated data, removing vm and nic_id
            kwargs = {k: v for k, v in data.items() if k not in ["vm", "nic_id"]}

            result = backend.update_nic(data["vm"], data["nic_id"], **kwargs)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        request=OpenNebulaNetworkListSerializer,
        responses={200: OpenApiResponse(description="List of NICs attached to VM")},
        description="List all network interfaces attached to a VM.",
    )
    @action(detail=False, methods=["get"])
    def list_nics(self, request):
        serializer = OpenNebulaNetworkListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            backend = OpenNebulaBackend(data["vm"].service_settings)
            nics = backend.list_nics(data["vm"])
            return Response(nics, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OpenNebulaNetworkViewSet(viewsets.ModelViewSet):
    queryset = OpenNebulaNetwork.objects.all()
    serializer_class = OpenNebulaNetworkSerializer

    @action(detail=True, methods=["post"])
    def update_network(self, request, pk=None):
        network = self.get_object()
        template = request.data.get("template")
        if not template:
            return Response(
                {"detail": "template is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        backend = OpenNebulaBackend(network.service_settings)
        try:
            backend.update_network(network, template)
            return Response(
                {"detail": "Network update scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def add_ar(self, request, pk=None):
        network = self.get_object()
        ar_template = request.data.get("ar_template")
        if not ar_template:
            return Response(
                {"detail": "ar_template is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        backend = OpenNebulaBackend(network.service_settings)
        try:
            backend.add_ar(network, ar_template)
            return Response(
                {"detail": "Address range add scheduled."},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def rm_ar(self, request, pk=None):
        network = self.get_object()
        ar_id = request.data.get("ar_id")
        force = request.data.get("force", False)
        if ar_id is None:
            return Response(
                {"detail": "ar_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        backend = OpenNebulaBackend(network.service_settings)
        try:
            backend.rm_ar(network, ar_id, force)
            return Response(
                {"detail": "Address range remove scheduled."},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def update_ar(self, request, pk=None):
        network = self.get_object()
        ar_template = request.data.get("ar_template")
        if not ar_template:
            return Response(
                {"detail": "ar_template is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        backend = OpenNebulaBackend(network.service_settings)
        try:
            backend.update_ar(network, ar_template)
            return Response(
                {"detail": "Address range update scheduled."},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def reserve_ar(self, request, pk=None):
        network = self.get_object()
        reservation_template = request.data.get("reservation_template")
        if not reservation_template:
            return Response(
                {"detail": "reservation_template is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        backend = OpenNebulaBackend(network.service_settings)
        try:
            backend.reserve_ar(network, reservation_template)
            return Response(
                {"detail": "Address reservation scheduled."},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "service_settings",
                type=int,
                required=True,
                location=OpenApiParameter.QUERY,
            )
        ],
        responses={200: OpenApiResponse(description="List of networks")},
        description="List available networks for VM deployment.",
    )
    @action(detail=False, methods=["get"])
    def list_all(self, request):
        service_settings_id = request.query_params.get("service_settings")
        if not service_settings_id:
            return Response(
                {"detail": "service_settings is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            settings = ServiceSettings.objects.get(pk=service_settings_id)
            client = OpenNebulaClient(settings)
            networks = client.list_networks()
            data = [
                {
                    "id": n.ID,
                    "name": n.NAME,
                    "bridge": getattr(n, "BRIDGE", None),
                    "vlan_id": getattr(n, "VLAN_ID", None),
                }
                for n in getattr(networks, "VNET", [])
            ]
            return Response(data)
        except ServiceSettings.DoesNotExist:
            return Response(
                {"detail": "ServiceSettings not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OpenNebulaVolumeViewSet(viewsets.ModelViewSet):
    queryset = OpenNebulaVolume.objects.all()
    serializer_class = OpenNebulaVolumeSerializer

    @action(detail=True, methods=["post"])
    def attach_to_vm(self, request, pk=None):
        volume = self.get_object()
        vm_id = request.data.get("vm_id")
        if not vm_id:
            return Response(
                {"detail": "vm_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        from .models import OpenNebulaVirtualMachine

        try:
            vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
        except OpenNebulaVirtualMachine.DoesNotExist:
            return Response(
                {"detail": "VM not found."}, status=status.HTTP_404_NOT_FOUND
            )
        backend = OpenNebulaBackend(volume.service_settings)
        try:
            backend.attach_disk(vm, volume)
            return Response(
                {"detail": "Attach scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def detach_from_vm(self, request, pk=None):
        volume = self.get_object()
        vm_id = request.data.get("vm_id")
        disk_id = request.data.get("disk_id")
        if not vm_id or not disk_id:
            return Response(
                {"detail": "vm_id and disk_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .models import OpenNebulaVirtualMachine

        try:
            vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
        except OpenNebulaVirtualMachine.DoesNotExist:
            return Response(
                {"detail": "VM not found."}, status=status.HTTP_404_NOT_FOUND
            )
        backend = OpenNebulaBackend(volume.service_settings)
        try:
            backend.detach_disk(vm, disk_id)
            return Response(
                {"detail": "Detach scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def create_snapshot(self, request, pk=None):
        volume = self.get_object()
        vm_id = request.data.get("vm_id")
        disk_id = request.data.get("disk_id")
        description = request.data.get("description")
        if not vm_id or not disk_id:
            return Response(
                {"detail": "vm_id and disk_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .models import OpenNebulaVirtualMachine

        try:
            vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
        except OpenNebulaVirtualMachine.DoesNotExist:
            return Response(
                {"detail": "VM not found."}, status=status.HTTP_404_NOT_FOUND
            )
        backend = OpenNebulaBackend(volume.service_settings)
        try:
            backend.create_disk_snapshot(vm, disk_id, description)
            return Response(
                {"detail": "Snapshot scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def delete_snapshot(self, request, pk=None):
        volume = self.get_object()
        vm_id = request.data.get("vm_id")
        disk_id = request.data.get("disk_id")
        snapshot_id = request.data.get("snapshot_id")
        if not vm_id or not disk_id or not snapshot_id:
            return Response(
                {"detail": "vm_id, disk_id, and snapshot_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .models import OpenNebulaVirtualMachine

        try:
            vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
        except OpenNebulaVirtualMachine.DoesNotExist:
            return Response(
                {"detail": "VM not found."}, status=status.HTTP_404_NOT_FOUND
            )
        backend = OpenNebulaBackend(volume.service_settings)
        try:
            backend.delete_disk_snapshot(vm, disk_id, snapshot_id)
            return Response(
                {"detail": "Snapshot delete scheduled."},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def revert_snapshot(self, request, pk=None):
        volume = self.get_object()
        vm_id = request.data.get("vm_id")
        disk_id = request.data.get("disk_id")
        snapshot_id = request.data.get("snapshot_id")
        if not vm_id or not disk_id or not snapshot_id:
            return Response(
                {"detail": "vm_id, disk_id, and snapshot_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .models import OpenNebulaVirtualMachine

        try:
            vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
        except OpenNebulaVirtualMachine.DoesNotExist:
            return Response(
                {"detail": "VM not found."}, status=status.HTTP_404_NOT_FOUND
            )
        backend = OpenNebulaBackend(volume.service_settings)
        try:
            backend.revert_disk_snapshot(vm, disk_id, snapshot_id)
            return Response(
                {"detail": "Snapshot revert scheduled."},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def rename_snapshot(self, request, pk=None):
        volume = self.get_object()
        vm_id = request.data.get("vm_id")
        disk_id = request.data.get("disk_id")
        snapshot_id = request.data.get("snapshot_id")
        new_name = request.data.get("new_name")
        if not vm_id or not disk_id or not snapshot_id or not new_name:
            return Response(
                {"detail": "vm_id, disk_id, snapshot_id, and new_name are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .models import OpenNebulaVirtualMachine

        try:
            vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
        except OpenNebulaVirtualMachine.DoesNotExist:
            return Response(
                {"detail": "VM not found."}, status=status.HTTP_404_NOT_FOUND
            )
        backend = OpenNebulaBackend(volume.service_settings)
        try:
            backend.rename_disk_snapshot(vm, disk_id, snapshot_id, new_name)
            return Response(
                {"detail": "Snapshot rename scheduled."},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def resize(self, request, pk=None):
        volume = self.get_object()
        vm_id = request.data.get("vm_id")
        disk_id = request.data.get("disk_id")
        size = request.data.get("size")
        if not vm_id or not disk_id or not size:
            return Response(
                {"detail": "vm_id, disk_id, and size are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .models import OpenNebulaVirtualMachine

        try:
            vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
        except OpenNebulaVirtualMachine.DoesNotExist:
            return Response(
                {"detail": "VM not found."}, status=status.HTTP_404_NOT_FOUND
            )
        backend = OpenNebulaBackend(volume.service_settings)
        try:
            backend.resize_disk(vm, disk_id, size)
            return Response(
                {"detail": "Resize scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def save_as_image(self, request, pk=None):
        volume = self.get_object()
        vm_id = request.data.get("vm_id")
        disk_id = request.data.get("disk_id")
        image_name = request.data.get("image_name")
        image_type = request.data.get("image_type", "")
        snapshot_id = request.data.get("snapshot_id", -1)
        if not vm_id or not disk_id or not image_name:
            return Response(
                {"detail": "vm_id, disk_id, and image_name are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .models import OpenNebulaVirtualMachine

        try:
            vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
        except OpenNebulaVirtualMachine.DoesNotExist:
            return Response(
                {"detail": "VM not found."}, status=status.HTTP_404_NOT_FOUND
            )
        backend = OpenNebulaBackend(volume.service_settings)
        try:
            backend.save_disk_as_image(vm, disk_id, image_name, image_type, snapshot_id)
            return Response(
                {"detail": "Save as image scheduled."}, status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    parameters=[
        OpenApiParameter(
            "service_settings", type=int, required=True, location=OpenApiParameter.QUERY
        )
    ],
    responses={200: OpenApiResponse(description="List of VM templates")},
    description="List available VM templates for deployment.",
)
class OpenNebulaTemplateListView(APIView):
    def get(self, request):
        service_settings_id = request.query_params.get("service_settings")
        if not service_settings_id:
            return Response(
                {"detail": "service_settings is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            settings = ServiceSettings.objects.get(pk=service_settings_id)
            client = OpenNebulaClient(settings)
            templates = client.list_templates()
            # Minimal serialization for wizard
            data = [
                {
                    "id": t.ID,
                    "name": t.NAME,
                    "cpu": getattr(t.TEMPLATE, "CPU", None),
                    "memory": getattr(t.TEMPLATE, "MEMORY", None),
                }
                for t in getattr(templates, "VMTEMPLATE", [])
            ]
            return Response(data)
        except ServiceSettings.DoesNotExist:
            return Response(
                {"detail": "ServiceSettings not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    parameters=[
        OpenApiParameter(
            "service_settings", type=int, required=True, location=OpenApiParameter.QUERY
        )
    ],
    responses={200: OpenApiResponse(description="List of images")},
    description="List available images for disk attach or VM creation.",
)
class OpenNebulaImageListView(APIView):
    def get(self, request):
        service_settings_id = request.query_params.get("service_settings")
        if not service_settings_id:
            return Response(
                {"detail": "service_settings is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            settings = ServiceSettings.objects.get(pk=service_settings_id)
            client = OpenNebulaClient(
                settings.backend_url, settings.username, settings.password
            )
            images = client.list_images()
            data = [
                {
                    "id": i.ID,
                    "name": i.NAME,
                    "size": getattr(i, "SIZE", None),
                    "type": getattr(i, "TYPE", None),
                }
                for i in getattr(images, "IMAGE", [])
            ]
            return Response(data)
        except ServiceSettings.DoesNotExist:
            return Response(
                {"detail": "ServiceSettings not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    request=OpenNebulaVMCreateSerializer,
    responses={
        201: OpenApiResponse(description="VM created"),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Backend error"),
    },
    description="Create a new VM with the selected template, networks, and options.",
)
class OpenNebulaVMCreateView(APIView):
    def post(self, request):
        serializer = OpenNebulaVMCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        settings = data["service_settings"]
        # Create DB record for VM in 'creating' state
        vm = OpenNebulaVirtualMachine.objects.create(
            name=data["name"],
            service_settings=settings,
            state="creating",
            # Add other required fields as needed (e.g., project, tenant)
        )
        # Schedule async Celery task
        create_vm_task(
            vm.pk,
            settings.pk,
            data["template_id"],
            data["name"],
            data["networks"],
            data.get("cpu"),
            data.get("ram"),
            data.get("disk"),
            data.get("ssh_key"),
            data.get("contextualization", False),
            data.get("extra", {}),
        )
        # Return VM object (with state) for polling
        return Response(
            OpenNebulaVirtualMachineSerializer(vm).data, status=status.HTTP_201_CREATED
        )


@extend_schema(
    request=OpenNebulaVMMigrateSerializer,
    responses={
        202: OpenApiResponse(description="Migration scheduled"),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Backend error"),
    },
    description="Migrate a VM to a target host/datastore.",
)
class OpenNebulaVMMigrateView(APIView):
    def post(self, request):
        serializer = OpenNebulaVMMigrateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        migrate_vm_task(
            vm.pk,
            data["host_id"],
            data.get("live", True),
            data.get("enforce", False),
            data.get("ds_id"),
            data.get("migration_type", 0),
        )
        return Response(
            {"detail": "Migration scheduled."}, status=status.HTTP_202_ACCEPTED
        )


@extend_schema(
    request=OpenNebulaDiskAttachSerializer,
    responses={
        202: OpenApiResponse(description="Disk attach scheduled"),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Backend error"),
    },
    description="Attach a disk/image to a VM.",
)
class OpenNebulaDiskAttachView(APIView):
    def post(self, request):
        serializer = OpenNebulaDiskAttachSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        disk_template = {
            "IMAGE_ID": data["image_id"],
        }
        if data.get("size"):
            disk_template["SIZE"] = data["size"]
        if data.get("type"):
            disk_template["TYPE"] = data["type"]
        if data.get("target"):
            disk_template["TARGET"] = data["target"]
        attach_disk_task(vm.pk, disk_template)
        return Response(
            {"detail": "Disk attach scheduled."}, status=status.HTTP_202_ACCEPTED
        )


@extend_schema(
    request=OpenNebulaDiskResizeSerializer,
    responses={
        202: OpenApiResponse(description="Disk resize scheduled"),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Backend error"),
    },
    description="Resize a disk attached to a VM.",
)
class OpenNebulaDiskResizeView(APIView):
    def post(self, request):
        serializer = OpenNebulaDiskResizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        resize_disk_task(vm.pk, data["disk_id"], data["size"])
        return Response(
            {"detail": "Disk resize scheduled."}, status=status.HTTP_202_ACCEPTED
        )


@extend_schema(
    request=OpenNebulaDiskSaveAsSerializer,
    responses={
        202: OpenApiResponse(description="Save disk as image scheduled"),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Backend error"),
    },
    description="Save a disk as a new image.",
)
class OpenNebulaDiskSaveAsView(APIView):
    def post(self, request):
        serializer = OpenNebulaDiskSaveAsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        save_disk_as_image_task(
            vm.pk,
            data["disk_id"],
            data["image_name"],
            data.get("image_type", ""),
            data.get("snapshot_id", -1),
        )
        return Response(
            {"detail": "Save as image scheduled."}, status=status.HTTP_202_ACCEPTED
        )


@extend_schema(
    request=OpenNebulaVMSnapshotSerializer,
    responses={
        202: OpenApiResponse(description="Snapshot creation scheduled"),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Backend error"),
    },
    description="Create a snapshot for a VM.",
)
class OpenNebulaVMSnapshotView(APIView):
    def post(self, request):
        serializer = OpenNebulaVMSnapshotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        create_vm_snapshot_task(data["vm"].pk, data["name"])
        return Response(
            {"detail": "Snapshot creation scheduled."}, status=status.HTTP_202_ACCEPTED
        )


@extend_schema(
    request=OpenNebulaVMListSnapshotsSerializer,
    responses={
        200: OpenApiResponse(description="List of VM snapshots"),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Backend error"),
    },
    description="List all snapshots for a VM.",
)
class OpenNebulaVMListSnapshotsView(APIView):
    def get(self, request):
        serializer = OpenNebulaVMListSnapshotsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        # Assume backend.list_snapshots(vm) returns a list of dicts
        try:
            backend = OpenNebulaBackend(vm.service_settings)
            snapshots = backend.list_snapshots(vm)
            return Response(snapshots, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    request=OpenNebulaBackupCreateSerializer,
    responses={
        202: OpenApiResponse(description="Backup creation scheduled"),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Backend error"),
    },
    description="Create a backup for a VM.",
)
class OpenNebulaBackupCreateView(APIView):
    def post(self, request):
        serializer = OpenNebulaBackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        create_backup_task(data["vm"].pk, data["name"], data.get("description", ""))
        return Response(
            {"detail": "Backup creation scheduled."}, status=status.HTTP_202_ACCEPTED
        )


@extend_schema(
    request=OpenNebulaBackupListSerializer,
    responses={
        200: OpenApiResponse(description="List of VM backups"),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Backend error"),
    },
    description="List all backups for a VM.",
)
class OpenNebulaBackupListView(APIView):
    def get(self, request):
        serializer = OpenNebulaBackupListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vm = data["vm"]
        try:
            backend = OpenNebulaBackend(vm.service_settings)
            backups = backend.list_backups(vm)
            return Response(backups, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    request=OpenNebulaRestoreBackupSerializer,
    responses={
        202: OpenApiResponse(description="Backup restore scheduled"),
        400: OpenApiResponse(description="Validation error"),
        500: OpenApiResponse(description="Backend error"),
    },
    description="Restore a backup to a VM or as a new VM.",
)
class OpenNebulaRestoreBackupView(APIView):
    def post(self, request):
        serializer = OpenNebulaRestoreBackupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        restore_backup_task(
            data["backup_id"],
            data.get("vm").pk if data.get("vm") else None,
            data.get("in_place", True),
            data.get("new_vm_name", ""),
        )
        return Response(
            {"detail": "Backup restore scheduled."}, status=status.HTTP_202_ACCEPTED
        )


@extend_schema(
    responses={
        200: OpenApiResponse(OpenNebulaMarketplaceOfferingSerializer(many=True)),
        500: OpenApiResponse(description="Backend error"),
    },
    description="List available marketplace offerings (templates/images).",
)
class OpenNebulaMarketplaceOfferingListView(APIView):
    def get(self, request):
        try:
            # Use the first available service_settings for demonstration; in production, filter by user/project
            from waldur_core.structure.models import ServiceSettings

            settings = ServiceSettings.objects.filter(type="OpenNebula").first()
            if not settings:
                return Response(
                    {"detail": "No OpenNebula service settings found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            backend = OpenNebulaBackend(settings)
            offerings = backend.list_marketplace_offerings()
            return Response(offerings, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    responses={200: OpenApiResponse(OpenNebulaVMMonitoringSerializer)},
    description="Get monitoring data for a VM.",
)
class OpenNebulaVMMonitoringView(APIView):
    def get(self, request, pk):
        vm = get_object_or_404(OpenNebulaVirtualMachine, pk=pk)
        backend = OpenNebulaBackend(vm.service_settings)
        data = backend.get_vm_monitoring(vm)
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    responses={200: OpenApiResponse(OpenNebulaVMMonitoringSerializer(many=True))},
    description="Get monitoring data for all VMs.",
)
class OpenNebulaVMPoolMonitoringView(APIView):
    def get(self, request):
        # Optionally filter by user/project
        backend = OpenNebulaBackend(
            ServiceSettings.objects.filter(type="OpenNebula").first()
        )
        data = backend.get_vmpool_monitoring()
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    responses={200: OpenApiResponse(OpenNebulaQuotaSerializer)},
    description="Get quota/usage for a tenant.",
)
class OpenNebulaQuotaView(APIView):
    def get(self, request, tenant_pk):
        tenant = get_object_or_404(OpenNebulaTenant, pk=tenant_pk)
        backend = OpenNebulaBackend(tenant.service_settings)
        data = backend.get_group_quota(tenant)
        return Response(data, status=status.HTTP_200_OK)


class OpenNebulaScheduledActionViewSet(viewsets.ModelViewSet):
    queryset = OpenNebulaScheduledAction.objects.all()
    serializer_class = OpenNebulaScheduledActionSerializer


class OpenNebulaTemplatesViewSet(viewsets.ViewSet):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "service_settings",
                type=int,
                required=True,
                location=OpenApiParameter.QUERY,
            )
        ],
        responses={200: OpenApiResponse(description="List of VM templates")},
        description="List available VM templates for deployment.",
    )
    def list(self, request):
        service_settings_id = request.query_params.get("service_settings")
        if not service_settings_id:
            return Response(
                {"detail": "service_settings is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            settings = ServiceSettings.objects.get(pk=service_settings_id)
            client = OpenNebulaClient(
                settings.backend_url, settings.username, settings.password
            )
            templates = client.list_templates()
            # Minimal serialization for wizard
            data = [
                {
                    "id": t.ID,
                    "name": t.NAME,
                    "cpu": getattr(t.TEMPLATE, "CPU", None),
                    "memory": getattr(t.TEMPLATE, "MEMORY", None),
                }
                for t in getattr(templates, "VMTEMPLATE", [])
            ]
            return Response(data)
        except ServiceSettings.DoesNotExist:
            return Response(
                {"detail": "ServiceSettings not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "service_settings",
                type=int,
                required=True,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                "id", type=int, required=True, location=OpenApiParameter.PATH
            ),
        ],
        responses={200: OpenApiResponse(description="Template details")},
        description="Get details of a specific VM template.",
    )
    def retrieve(self, request, pk=None):  # TODO: Implentation
        service_settings_id = request.query_params.get("service_settings")
        if not service_settings_id:
            return Response(
                {"detail": "service_settings is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ServiceSettings.objects.get(pk=service_settings_id)
            # template = client.get_template(pk) - TODO GET TEMPLATE
            template = ""
            if not template:
                return Response(
                    {"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND
                )

            # Extract template details
            data = {
                "id": template.ID,
                "name": template.NAME,
                "cpu": getattr(template.TEMPLATE, "CPU", None),
                "memory": getattr(template.TEMPLATE, "MEMORY", None),
                "disk": getattr(template.TEMPLATE, "DISK", []),
                "nic": getattr(template.TEMPLATE, "NIC", []),
                "template_data": template.TEMPLATE.toxml(),
            }
            return Response(data)
        except ServiceSettings.DoesNotExist:
            return Response(
                {"detail": "ServiceSettings not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OpenNebulaImagesViewSet(viewsets.ViewSet):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "service_settings",
                type=int,
                required=True,
                location=OpenApiParameter.QUERY,
            )
        ],
        responses={200: OpenApiResponse(description="List of images")},
        description="List available images for disk attach or VM creation.",
    )
    def list(self, request):
        service_settings_id = request.query_params.get("service_settings")
        if not service_settings_id:
            return Response(
                {"detail": "service_settings is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            settings = ServiceSettings.objects.get(pk=service_settings_id)
            client = OpenNebulaClient(
                settings.backend_url, settings.username, settings.password
            )
            images = client.list_images()
            data = [
                {
                    "id": i.ID,
                    "name": i.NAME,
                    "size": getattr(i, "SIZE", None),
                    "type": getattr(i, "TYPE", None),
                }
                for i in getattr(images, "IMAGE", [])
            ]
            return Response(data)
        except ServiceSettings.DoesNotExist:
            return Response(
                {"detail": "ServiceSettings not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "service_settings",
                type=int,
                required=True,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                "id", type=int, required=True, location=OpenApiParameter.PATH
            ),
        ],
        responses={200: OpenApiResponse(description="Image details")},
        description="Get details of a specific image.",
    )
    def retrieve(self, request, pk=None):  # TODO: Implentation
        service_settings_id = request.query_params.get("service_settings")
        if not service_settings_id:
            return Response(
                {"detail": "service_settings is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ServiceSettings.objects.get(pk=service_settings_id)
            # image = client.get_image(pk)
            image = ""
            if not image:
                return Response(
                    {"detail": "Image not found."}, status=status.HTTP_404_NOT_FOUND
                )

            # Extract image details
            data = {
                "id": image.ID,
                "name": image.NAME,
                "size": getattr(image, "SIZE", None),
                "type": getattr(image, "TYPE", None),
                "persistent": getattr(image, "PERSISTENT", None),
                "format": getattr(image, "FORMAT", None),
                "state": getattr(image, "STATE", None),
                "image_data": image.toxml(),
            }
            return Response(data)
        except ServiceSettings.DoesNotExist:
            return Response(
                {"detail": "ServiceSettings not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
