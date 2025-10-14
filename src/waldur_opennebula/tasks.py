# Place for OpenNebula Celery tasks
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from waldur_core.structure.models import ServiceSettings
from waldur_opennebula.backend import OpenNebulaBackend
from waldur_opennebula.models import (
    OpenNebulaTenant,
    OpenNebulaVirtualMachine,
)

from .client import OpenNebulaClient
from .models import OpenNebulaScheduledAction


@shared_task
def create_vm_task(
    vm_id,
    service_settings_id,
    template_id,
    name,
    networks,
    cpu=None,
    ram=None,
    disk=None,
    ssh_key=None,
    contextualization=False,
    extra=None,
):
    settings = ServiceSettings.objects.get(pk=service_settings_id)
    client = OpenNebulaClient(settings.backend_url)
    params = extra.copy() if extra else {}
    if cpu is not None:
        params["CPU"] = cpu
    if ram is not None:
        params["MEMORY"] = ram
    if disk is not None:
        params["DISK_SIZE"] = disk
    if ssh_key:
        params["SSH_PUBLIC_KEY"] = ssh_key
    if contextualization:
        params["CONTEXT"] = {"SSH_PUBLIC_KEY": ssh_key} if ssh_key else {}
    params["NIC"] = [{"NETWORK_ID": net_id} for net_id in networks]
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    vm.begin_creating()
    vm.progress = 0
    vm.error_message = ""
    vm.save(update_fields=["state", "progress", "error_message"])
    try:
        vm.progress = 50
        vm.save(update_fields=["progress"])
        vm.backend_id = client.create_vm(template_id, name=name, extra=params)
        vm.set_ok()
        vm.progress = 100
        vm.save(update_fields=["state", "backend_id", "progress"])
    except Exception as e:
        vm.set_erred()
        vm.error_message = str(e)
        vm.progress = 0
        vm.save(update_fields=["state", "error_message", "progress"])
        raise


@shared_task
def delete_vm_task(vm_id):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    vm.schedule_deleting()
    vm.save(update_fields=["state"])
    backend = OpenNebulaBackend(vm.service_settings)
    try:
        backend.delete_vm(vm)
    except Exception:
        vm.set_erred()
        vm.save(update_fields=["state"])


@shared_task
def start_vm_task(vm_id):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    vm.begin_creating()  # Or a custom state for starting
    vm.save(update_fields=["state"])
    backend = OpenNebulaBackend(vm.service_settings)
    try:
        backend.start_vm(vm)
        vm.set_ok()
        vm.save(update_fields=["state"])
    except Exception:
        vm.set_erred()
        vm.save(update_fields=["state"])


@shared_task
def stop_vm_task(vm_id):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    vm.begin_creating()  # Or a custom state for stopping
    vm.save(update_fields=["state"])
    backend = OpenNebulaBackend(vm.service_settings)
    try:
        backend.stop_vm(vm)
        vm.set_ok()
        vm.save(update_fields=["state"])
    except Exception:
        vm.set_erred()
        vm.save(update_fields=["state"])


@shared_task
def create_tenant_task(tenant_id):
    tenant = OpenNebulaTenant.objects.get(pk=tenant_id)
    backend = OpenNebulaBackend(tenant.service_settings)
    try:
        backend.create_tenant(tenant)
    except Exception:
        pass


@shared_task
def delete_tenant_task(tenant_id):
    tenant = OpenNebulaTenant.objects.get(pk=tenant_id)
    backend = OpenNebulaBackend(tenant.service_settings)
    try:
        backend.delete_tenant(tenant)
    except Exception:
        pass


@shared_task(name="opennebula.pull_tenants_task")
def pull_tenants_task(service_settings_id):
    settings = ServiceSettings.objects.get(pk=service_settings_id)
    backend = OpenNebulaBackend(settings)
    backend.pull_tenants()


@shared_task
def attach_disk_task(vm_id, disk_template):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    vm.progress = 0
    vm.error_message = ""
    vm.save(update_fields=["progress", "error_message"])
    try:
        vm.progress = 50
        vm.save(update_fields=["progress"])
        backend.attach_disk(vm, disk_template)
        vm.progress = 100
        vm.set_ok()
        vm.save(update_fields=["progress", "state"])
    except Exception as e:
        vm.set_erred()
        vm.error_message = str(e)
        vm.progress = 0
        vm.save(update_fields=["state", "error_message", "progress"])
        raise


@shared_task
def detach_disk_task(vm_id, disk_id):
    from .models import OpenNebulaVolume

    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    # Find the volume by disk_id if possible
    try:
        volume = OpenNebulaVolume.objects.get(backend_id=disk_id)
    except OpenNebulaVolume.DoesNotExist:
        volume = None
    if volume:
        volume.progress = 0
        volume.error_message = ""
        volume.save(update_fields=["progress", "error_message"])
    try:
        if volume:
            volume.progress = 50
            volume.save(update_fields=["progress"])
        backend.detach_disk(vm, disk_id)
        vm.set_ok()
        if volume:
            volume.progress = 100
            volume.save(update_fields=["progress"])
        vm.save(update_fields=["state"])
    except Exception as e:
        vm.set_erred()
        if volume:
            volume.error_message = str(e)
            volume.progress = 0
            volume.save(update_fields=["error_message", "progress"])
        vm.save(update_fields=["state"])


@shared_task
def resize_disk_task(vm_id, disk_id, size):
    from .models import OpenNebulaVolume

    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    try:
        volume = OpenNebulaVolume.objects.get(backend_id=disk_id)
    except OpenNebulaVolume.DoesNotExist:
        volume = None
    if volume:
        volume.progress = 0
        volume.error_message = ""
        volume.save(update_fields=["progress", "error_message"])
    try:
        if volume:
            volume.progress = 50
            volume.save(update_fields=["progress"])
        backend.resize_disk(vm, disk_id, size)
        vm.set_ok()
        if volume:
            volume.progress = 100
            volume.save(update_fields=["progress"])
        vm.save(update_fields=["state"])
    except Exception as e:
        vm.set_erred()
        if volume:
            volume.error_message = str(e)
            volume.progress = 0
            volume.save(update_fields=["error_message", "progress"])
        vm.save(update_fields=["state"])


@shared_task
def create_disk_snapshot_task(vm_id, disk_id, description=None):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    try:
        backend.create_disk_snapshot(vm, disk_id, description)
        vm.set_ok()
        vm.save(update_fields=["state"])
    except Exception:
        vm.set_erred()
        vm.save(update_fields=["state"])


@shared_task
def delete_disk_snapshot_task(vm_id, disk_id, snapshot_id):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    try:
        backend.delete_disk_snapshot(vm, disk_id, snapshot_id)
        vm.set_ok()
        vm.save(update_fields=["state"])
    except Exception:
        vm.set_erred()
        vm.save(update_fields=["state"])


@shared_task
def revert_disk_snapshot_task(vm_id, disk_id, snapshot_id):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    try:
        backend.revert_disk_snapshot(vm, disk_id, snapshot_id)
        vm.set_ok()
        vm.save(update_fields=["state"])
    except Exception:
        vm.set_erred()
        vm.save(update_fields=["state"])


@shared_task
def rename_disk_snapshot_task(vm_id, disk_id, snapshot_id, new_name):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    try:
        backend.rename_disk_snapshot(vm, disk_id, snapshot_id, new_name)
        vm.set_ok()
        vm.save(update_fields=["state"])
    except Exception:
        vm.set_erred()
        vm.save(update_fields=["state"])


@shared_task
def save_disk_as_image_task(vm_id, disk_id, image_name, image_type="", snapshot_id=-1):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    vm.progress = 0
    vm.error_message = ""
    vm.save(update_fields=["progress", "error_message"])
    try:
        vm.progress = 50
        vm.save(update_fields=["progress"])
        backend.save_disk_as_image(vm, disk_id, image_name, image_type, snapshot_id)
        vm.progress = 100
        vm.set_ok()
        vm.save(update_fields=["progress", "state"])
    except Exception as e:
        vm.set_erred()
        vm.error_message = str(e)
        vm.progress = 0
        vm.save(update_fields=["state", "error_message", "progress"])
        raise


@shared_task
def backup_vm_task(vm_id, ds_id, reset=False):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    try:
        backend.backup_vm(vm, ds_id, reset)
        vm.set_ok()
        vm.save(update_fields=["state"])
    except Exception:
        vm.set_erred()
        vm.save(update_fields=["state"])


@shared_task
def backup_cancel_task(vm_id):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    try:
        backend.backup_cancel(vm)
        vm.set_ok()
        vm.save(update_fields=["state"])
    except Exception:
        vm.set_erred()
        vm.save(update_fields=["state"])


@shared_task
def restore_vm_task(vm_id, backup_id, in_place=True):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    try:
        backend.restore_vm(vm, backup_id, in_place)
        vm.set_ok()
        vm.save(update_fields=["state"])
    except Exception:
        vm.set_erred()
        vm.save(update_fields=["state"])


@shared_task
def add_ar_task(network_id, ar_template):
    from .models import OpenNebulaNetwork

    network = OpenNebulaNetwork.objects.get(pk=network_id)
    backend = OpenNebulaBackend(network.service_settings)
    network.progress = 0
    network.error_message = ""
    network.save(update_fields=["progress", "error_message"])
    try:
        network.progress = 50
        network.save(update_fields=["progress"])
        backend.add_ar(network, ar_template)
        network.progress = 100
        network.save(update_fields=["progress"])
    except Exception as e:
        network.error_message = str(e)
        network.progress = 0
        network.save(update_fields=["error_message", "progress"])
        raise


@shared_task
def rm_ar_task(network_id, ar_id, force=False):
    from .models import OpenNebulaNetwork

    network = OpenNebulaNetwork.objects.get(pk=network_id)
    backend = OpenNebulaBackend(network.service_settings)
    network.progress = 0
    network.error_message = ""
    network.save(update_fields=["progress", "error_message"])
    try:
        network.progress = 50
        network.save(update_fields=["progress"])
        backend.rm_ar(network, ar_id, force)
        network.progress = 100
        network.save(update_fields=["progress"])
    except Exception as e:
        network.error_message = str(e)
        network.progress = 0
        network.save(update_fields=["error_message", "progress"])
        raise


@shared_task
def update_ar_task(network_id, ar_template):
    from .models import OpenNebulaNetwork

    network = OpenNebulaNetwork.objects.get(pk=network_id)
    backend = OpenNebulaBackend(network.service_settings)
    network.progress = 0
    network.error_message = ""
    network.save(update_fields=["progress", "error_message"])
    try:
        network.progress = 50
        network.save(update_fields=["progress"])
        backend.update_ar(network, ar_template)
        network.progress = 100
        network.save(update_fields=["progress"])
    except Exception as e:
        network.error_message = str(e)
        network.progress = 0
        network.save(update_fields=["error_message", "progress"])
        raise


@shared_task
def reserve_ar_task(network_id, reservation_template):
    from .models import OpenNebulaNetwork

    network = OpenNebulaNetwork.objects.get(pk=network_id)
    backend = OpenNebulaBackend(network.service_settings)
    network.progress = 0
    network.error_message = ""
    network.save(update_fields=["progress", "error_message"])
    try:
        network.progress = 50
        network.save(update_fields=["progress"])
        backend.reserve_ar(network, reservation_template)
        network.progress = 100
        network.save(update_fields=["progress"])
    except Exception as e:
        network.error_message = str(e)
        network.progress = 0
        network.save(update_fields=["error_message", "progress"])
        raise


@shared_task
def migrate_vm_task(
    vm_id, host_id, live=True, enforce=False, ds_id=None, migration_type=0
):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    vm.progress = 0
    vm.error_message = ""
    vm.save(update_fields=["progress", "error_message"])
    try:
        vm.progress = 50
        vm.save(update_fields=["progress"])
        backend.migrate_vm(vm, host_id, live, enforce, ds_id, migration_type)
        vm.progress = 100
        vm.set_ok()
        vm.save(update_fields=["progress", "state"])
    except Exception as e:
        vm.set_erred()
        vm.error_message = str(e)
        vm.progress = 0
        vm.save(update_fields=["state", "error_message", "progress"])
        raise


@shared_task
def create_vm_snapshot_task(vm_id, name):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    vm.progress = 0
    vm.error_message = ""
    vm.save(update_fields=["progress", "error_message"])
    try:
        vm.progress = 50
        vm.save(update_fields=["progress"])
        backend.create_snapshot(vm, name)
        vm.progress = 100
        vm.set_ok()
        vm.save(update_fields=["progress", "state"])
    except Exception as e:
        vm.set_erred()
        vm.error_message = str(e)
        vm.progress = 0
        vm.save(update_fields=["state", "error_message", "progress"])
        raise


@shared_task
def restore_vm_snapshot_task(vm_id, snapshot_id):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    vm.progress = 0
    vm.error_message = ""
    vm.save(update_fields=["progress", "error_message"])
    try:
        vm.progress = 50
        vm.save(update_fields=["progress"])
        backend.restore_vm_snapshot(vm, snapshot_id)
        vm.progress = 100
        vm.set_ok()
        vm.save(update_fields=["progress", "state"])
    except Exception as e:
        vm.set_erred()
        vm.error_message = str(e)
        vm.progress = 0
        vm.save(update_fields=["state", "error_message", "progress"])
        raise


@shared_task
def create_backup_task(vm_id, name, description=None):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)
    vm.progress = 0
    vm.error_message = ""
    vm.save(update_fields=["progress", "error_message"])
    try:
        vm.progress = 50
        vm.save(update_fields=["progress"])
        backend.create_backup(vm, name, description)
        vm.progress = 100
        vm.set_ok()
        vm.save(update_fields=["progress", "state"])
    except Exception as e:
        vm.set_erred()
        vm.error_message = str(e)
        vm.progress = 0
        vm.save(update_fields=["state", "error_message", "progress"])
        raise


@shared_task
def restore_backup_task(backup_id, vm_id=None, in_place=True, new_vm_name=None):
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id) if vm_id else None
    backend = OpenNebulaBackend(vm.service_settings) if vm else None
    if vm:
        vm.progress = 0
        vm.error_message = ""
        vm.save(update_fields=["progress", "error_message"])
    try:
        if vm:
            if backend:
                vm.progress = 50
                vm.save(update_fields=["progress"])
                backend.restore_backup(backup_id, vm, in_place, new_vm_name)
                vm.progress = 100
                vm.set_ok()
                vm.save(update_fields=["progress", "state"])
        else:
            # For new VM, just call backend.restore_backup
            OpenNebulaBackend(None).restore_backup(backup_id, None, False, new_vm_name)
    except Exception as e:
        if vm:
            vm.set_erred()
            vm.error_message = str(e)
            vm.progress = 0
            vm.save(update_fields=["state", "error_message", "progress"])
        raise


@shared_task
def run_scheduled_actions():
    now = timezone.now()
    for action in OpenNebulaScheduledAction.objects.filter(
        enabled=True, next_run__lte=now
    ):
        try:
            if action.action_type == "snapshot":
                create_vm_snapshot_task.delay(
                    action.vm.pk, action.params.get("name", f"auto-{now:%Y%m%d%H%M}")
                )
            elif action.action_type == "backup":
                create_backup_task.delay(
                    action.vm.pk,
                    action.params.get("name", f"auto-backup-{now:%Y%m%d%H%M}"),
                )
            action.last_run = now
            # Calculate next_run based on interval
            if action.interval == "daily":
                action.next_run = now + timedelta(days=1)
            elif action.interval == "weekly":
                action.next_run = now + timedelta(weeks=1)
            # Add more interval logic as needed
            action.error_message = ""
        except Exception as e:
            action.error_message = str(e)
        action.save()


@shared_task
def list_backups_task(vm_id):
    """
    Task to list all backups of a specific virtual machine.

    Args:
        vm_id: ID of the OpenNebulaVirtualMachine

    Returns:
        List of backups for the specified VM
    """
    vm = OpenNebulaVirtualMachine.objects.get(pk=vm_id)
    backend = OpenNebulaBackend(vm.service_settings)

    try:
        backups = backend.list_backups(vm)
        return backups
    except Exception as e:
        vm.error_message = f"Failed to list backups: {str(e)}"
        vm.save(update_fields=["error_message"])
        raise
