from celery import chain
from waldur_core.core import executors as core_executors
from waldur_core.core import tasks as core_tasks
from waldur_core.core import utils as core_utils
from waldur_core.structure import executors as structure_executors
from waldur_opennebula import tasks
from . import models


def pull_datastores_for_resource(instance, task):
    # passthrough; no datastores in OpenNebula
    return task


class VirtualMachinePullExecutor(core_executors.ActionExecutor):
    action = 'Pull'
    @classmethod
    def get_task_signature(cls, instance, serialized_instance, **kwargs):
        return core_tasks.BackendMethodTask().si(
            serialized_instance,
            'pull_vms',
            state_transition='begin_updating',
        )


class VirtualMachineCreateExecutor(core_executors.CreateExecutor):
    @classmethod
    def get_task_signature(cls, instance, serialized_instance, **kwargs):
        initial = core_tasks.BackendMethodTask().si(
            serialized_instance,
            'create_vm',
            state_transition='begin_creating',
        )
        return chain(
            pull_datastores_for_resource(instance, initial),
            core_tasks.BackendMethodTask().si(serialized_instance, 'pull_vms'),
        )


class VirtualMachineDeleteExecutor(core_executors.DeleteExecutor):
    @classmethod
    def get_task_signature(cls, instance, serialized_instance, **kwargs):
        if instance.backend_id:
            task = core_tasks.BackendMethodTask().si(
                serialized_instance,
                'delete_vm',
                state_transition='begin_deleting',
            )
            return pull_datastores_for_resource(instance, task)
        return core_tasks.StateTransitionTask().si(
            serialized_instance, state_transition='begin_deleting'
        )


class VirtualMachineStartExecutor(core_executors.ActionExecutor):
    action = 'Start'
    @classmethod
    def get_task_signature(cls, instance, serialized_instance, **kwargs):
        return chain(
            core_tasks.BackendMethodTask().si(
                serialized_instance,
                'start_vm',
                state_transition='begin_updating',
            ),
            core_tasks.BackendMethodTask().si(serialized_instance, 'pull_vms'),
        )


class VirtualMachineStopExecutor(core_executors.ActionExecutor):
    action = 'Stop'
    @classmethod
    def get_task_signature(cls, instance, serialized_instance, **kwargs):
        return chain(
            core_tasks.BackendMethodTask().si(
                serialized_instance,
                'stop_vm',
                state_transition='begin_updating',
            ),
            core_tasks.BackendMethodTask().si(serialized_instance, 'pull_vms'),
        )


class VirtualMachineRebootExecutor(core_executors.ActionExecutor):
    action = 'Reboot'
    @classmethod
    def get_task_signature(cls, instance, serialized_instance, **kwargs):
        return chain(
            core_tasks.BackendMethodTask().si(
                serialized_instance,
                'reboot_vm',
                state_transition='begin_updating',
            ),
            core_tasks.PollBackendCheckTask().si(serialized_instance, 'is_virtual_machine_powered_off'),
            core_tasks.PollBackendCheckTask().si(serialized_instance, 'is_virtual_machine_powered_on'),
            core_tasks.BackendMethodTask().si(serialized_instance, 'pull_vms'),
        )


class TenantCreateExecutor(core_executors.CreateExecutor):
    @classmethod
    def get_task_signature(cls, instance, serialized_instance, **kwargs):
        return core_tasks.BackendMethodTask().si(
            serialized_instance,
            'create_tenant',
            state_transition='begin_creating',
        )


class TenantDeleteExecutor(core_executors.DeleteExecutor):
    @classmethod
    def get_task_signature(cls, instance, serialized_instance, **kwargs):
        if instance.backend_id:
            return core_tasks.BackendMethodTask().si(
                serialized_instance,
                'delete_tenant',
                state_transition='begin_deleting',
            )
        return core_tasks.StateTransitionTask().si(
            serialized_instance, state_transition='begin_deleting'
        )


class TenantPullExecutor(core_executors.ActionExecutor):
    action = 'Pull'
    @classmethod
    def get_task_signature(cls, service_settings, serialized_settings, **kwargs):
        return core_tasks.BackendMethodTask().si(serialized_settings, 'pull_tenants')


# TODO: Refactor disk, snapshot, network, volume executors to use core_executors and core_tasks.si


class AttachDiskExecutor(core_executors.ActionExecutor):
    action = 'Attach'
    @classmethod
    def get_task_signature(cls, vm, volume, **kwargs):
        return tasks.attach_disk_task(vm.pk, volume.pk)


class DetachDiskExecutor(core_executors.ActionExecutor):
    action = 'Detach'
    @classmethod
    def get_task_signature(cls, vm, disk_id, **kwargs):
        return tasks.detach_disk_task(vm.pk, disk_id)


class NetworkDeleteExecutor(core_executors.DeleteExecutor):
    @classmethod
    def get_task_signature(cls, instance, serialized_instance, **kwargs):
        if instance.backend_id:
            return core_tasks.BackendMethodTask().si(
                serialized_instance,
                'delete_network',
                state_transition='begin_deleting',
            )
        return core_tasks.StateTransitionTask().si(
            serialized_instance, state_transition='begin_deleting'
        )


class VolumeDeleteExecutor(core_executors.DeleteExecutor):
    @classmethod
    def get_task_signature(cls, instance, serialized_instance, **kwargs):
        if instance.backend_id:
            return core_tasks.BackendMethodTask().si(
                serialized_instance,
                'delete_volume',
                state_transition='begin_deleting',
            )
        return core_tasks.StateTransitionTask().si(
            serialized_instance, state_transition='begin_deleting'
        )

class ResizeDiskExecutor(core_executors.ActionExecutor):
    action = 'Resize'
    @classmethod
    def get_task_signature(cls, vm, disk_id, size, **kwargs):
        return tasks.resize_disk_task(vm.pk, disk_id, size)


class CreateDiskSnapshotExecutor(core_executors.ActionExecutor):
    action = 'Create'
    @classmethod
    def get_task_signature(cls, vm, disk_id, description=None, **kwargs):
        return tasks.create_disk_snapshot_task(vm.pk, disk_id, description)


class DeleteDiskSnapshotExecutor(core_executors.ActionExecutor):
    action = 'Delete'
    @classmethod
    def get_task_signature(cls, vm, disk_id, snapshot_id, **kwargs):
        return tasks.delete_disk_snapshot_task(vm.pk, disk_id, snapshot_id)


class RevertDiskSnapshotExecutor(core_executors.ActionExecutor):
    action = 'Revert'
    @classmethod
    def get_task_signature(cls, vm, disk_id, snapshot_id, **kwargs):
        return tasks.revert_disk_snapshot_task(vm.pk, disk_id, snapshot_id)


class RenameDiskSnapshotExecutor(core_executors.ActionExecutor):
    action = 'Rename'
    @classmethod
    def get_task_signature(cls, vm, disk_id, snapshot_id, new_name, **kwargs):
        return tasks.rename_disk_snapshot_task(vm.pk, disk_id, snapshot_id, new_name)


class SaveDiskAsImageExecutor(core_executors.ActionExecutor):
    action = 'Save'
    @classmethod
    def get_task_signature(cls, vm, disk_id, image_name, image_type="", snapshot_id=-1, **kwargs):
        return tasks.save_disk_as_image_task(vm.pk, disk_id, image_name, image_type, snapshot_id)


class BackupVMExecutor(core_executors.ActionExecutor):
    action = 'Backup'
    @classmethod
    def get_task_signature(cls, vm, ds_id, reset=False, **kwargs):
        return tasks.backup_vm_task(vm.pk, ds_id, reset)


class BackupCancelExecutor(core_executors.ActionExecutor):
    action = 'Cancel'
    @classmethod
    def get_task_signature(cls, vm, **kwargs):
        return tasks.backup_cancel_task(vm.pk)


class RestoreVMExecutor(core_executors.ActionExecutor):
    action = 'Restore'
    @classmethod
    def get_task_signature(cls, vm, backup_id, in_place=True, **kwargs):
        return tasks.restore_vm_task(vm.pk, backup_id, in_place)
    


class OpenNebulaCleanupExecutor(structure_executors.BaseCleanupExecutor):
    executors = (
        (models.OpenNebulaVolume, VolumeDeleteExecutor),
        (models.OpenNebulaNetwork, NetworkDeleteExecutor),
        (models.OpenNebulaVirtualMachine, VirtualMachineDeleteExecutor),
        (models.OpenNebulaTenant, TenantDeleteExecutor),)