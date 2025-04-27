import pyone
import logging
from .exceptions import OpenNebulaError

logger = logging.getLogger(__name__)


class OpenNebulaClient:
    def __init__(self, endpoint, username, password):
        self.one = pyone.OneServer(endpoint, session="%s:%s" % (username, password))

    def get_version(self):
        """
        Returns the OpenNebula system version.
        :return: Version string
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.system.version()
        except pyone.OneException as e:
            logger.exception('Failed to get OpenNebula version')
            raise OpenNebulaError(e)

    def list_vms(self):
        """
        Returns a list of all VMs (Virtual Machines) in OpenNebula.
        :return: VM pool information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vmpool.info(-2, -1, -1, -1, -1)
        except pyone.OneException as e:
            logger.exception('Failed to list VMs')
            raise OpenNebulaError(e)

    def get_vm(self, vm_id):
        """
        Returns information about a specific VM.
        :param vm_id: VM identifier
        :type vm_id: int
        :return: VM information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.info(vm_id)
        except pyone.OneException as e:
            logger.exception('Failed to get VM info')
            raise OpenNebulaError(e)

    def create_vm(self, template_id, name=None, extra=None):
        """
        Creates a VM from a template. Optionally set name and extra attributes.
        :param template_id: Template identifier
        :type template_id: int
        :param name: Optional VM name
        :type name: str or None
        :param extra: Optional extra attributes (CPU, RAM, etc.)
        :type extra: dict or None
        :return: VM identifier
        :raises OpenNebulaError: If the API call fails
        """
        try:
            params = {}
            if name:
                params['NAME'] = name
            if extra:
                params.update(extra)
            return self.one.vm.allocate(template_id, params)
        except pyone.OneException as e:
            logger.exception('Failed to create VM')
            raise OpenNebulaError(e)

    def delete_vm(self, vm_id):
        """
        Deletes a VM by ID.
        :param vm_id: VM identifier
        :type vm_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.action('delete', vm_id)
        except pyone.OneException as e:
            logger.exception('Failed to delete VM')
            raise OpenNebulaError(e)

    def start_vm(self, vm_id):
        """
        Starts a VM by ID.
        :param vm_id: VM identifier
        :type vm_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.action('resume', vm_id)
        except pyone.OneException as e:
            logger.exception('Failed to start VM')
            raise OpenNebulaError(e)

    def stop_vm(self, vm_id):
        """
        Stops (powers off) a VM by ID.
        :param vm_id: VM identifier
        :type vm_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.action('poweroff', vm_id)
        except pyone.OneException as e:
            logger.exception('Failed to stop VM')
            raise OpenNebulaError(e)

    def reboot_vm(self, vm_id):
        """
        Reboots a VM by ID.
        :param vm_id: VM identifier
        :type vm_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.action('reboot', vm_id)
        except pyone.OneException as e:
            logger.exception('Failed to reboot VM')
            raise OpenNebulaError(e)

    def resize_vm(self, vm_id, cpu=None, ram=None):
        """
        Updates a VM's CPU/RAM.
        :param vm_id: VM identifier
        :type vm_id: int
        :param cpu: New CPU value
        :type cpu: float or None
        :param ram: New RAM value in MB
        :type ram: int or None
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            template = {}
            if cpu is not None:
                template['CPU'] = cpu
            if ram is not None:
                template['MEMORY'] = ram
            return self.one.vm.update(vm_id, template, 1)  # 1 = merge
        except pyone.OneException as e:
            logger.exception('Failed to resize VM')
            raise OpenNebulaError(e)

    def attach_disk(self, vm_id, disk_template):
        """
        Attaches a new disk to the VM.
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_template: Disk configuration
        :type disk_template: dict
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.attach(vm_id, disk_template)
        except pyone.OneException as e:
            logger.exception('Failed to attach disk to VM')
            raise OpenNebulaError(e)

    def detach_disk(self, vm_id, disk_id):
        """
        Detaches a disk from the VM.
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.detach(vm_id, disk_id)
        except pyone.OneException as e:
            logger.exception('Failed to detach disk from VM')
            raise OpenNebulaError(e)

    def snapshot_vm(self, vm_id, name):
        """
        Creates a snapshot for a VM.
        :param vm_id: VM identifier
        :type vm_id: int
        :param name: Snapshot name
        :type name: str
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.snapshot_create(vm_id, name)
        except pyone.OneException as e:
            logger.exception('Failed to create VM snapshot')
            raise OpenNebulaError(e)

    def restore_vm_snapshot(self, vm_id, snapshot_id):
        """
        Restores a VM from a snapshot.
        :param vm_id: VM identifier
        :type vm_id: int
        :param snapshot_id: Snapshot identifier
        :type snapshot_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.snapshot_revert(vm_id, snapshot_id)
        except pyone.OneException as e:
            logger.exception('Failed to restore VM snapshot')
            raise OpenNebulaError(e)

    def get_console(self, vm_id):
        """
        Retrieves VM console information.
        :param vm_id: VM identifier
        :type vm_id: int
        :return: Console information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.console(vm_id)
        except pyone.OneException as e:
            logger.exception('Failed to get VM console info')
            raise OpenNebulaError(e)

    # Tenant (group/project) management
    def list_groups(self):
        """
        Lists all user groups.
        :return: Group pool information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.grouppool.info()
        except pyone.OneException as e:
            logger.exception('Failed to list groups')
            raise OpenNebulaError(e)

    def get_group(self, group_id):
        """
        Retrieves information about a specific group.
        :param group_id: Group identifier
        :type group_id: int
        :return: Group information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.group.info(group_id)
        except pyone.OneException as e:
            logger.exception('Failed to get group info')
            raise OpenNebulaError(e)

    def create_group(self, name, description=None):
        """
        Creates a new user group.
        :param name: Group name
        :type name: str
        :param description: Group description
        :type description: str or None
        :return: Group identifier
        :raises OpenNebulaError: If the API call fails
        """
        try:
            params = {'NAME': name}
            if description:
                params['DESCRIPTION'] = description
            return self.one.group.allocate(params)
        except pyone.OneException as e:
            logger.exception('Failed to create group')
            raise OpenNebulaError(e)

    def delete_group(self, group_id):
        """
        Deletes a user group.
        :param group_id: Group identifier
        :type group_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.group.delete(group_id)
        except pyone.OneException as e:
            logger.exception('Failed to delete group')
            raise OpenNebulaError(e)

    def list_networks(self):
        """
        Lists all virtual networks.
        :return: Virtual network pool information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vnpool.info()
        except pyone.OneException as e:
            logger.exception('Failed to list networks')
            raise OpenNebulaError(e)

    def get_network(self, network_id):
        """
        Retrieves information about a specific virtual network.
        :param network_id: Network identifier
        :type network_id: int
        :return: Virtual network information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vn.info(network_id)
        except pyone.OneException as e:
            logger.exception('Failed to get network info')
            raise OpenNebulaError(e)

    def create_network(self, name, description=None):
        """
        Creates a new virtual network.
        :param name: Network name
        :type name: str
        :param description: Network description
        :type description: str or None
        :return: Network identifier
        :raises OpenNebulaError: If the API call fails
        """
        try:
            params = {'NAME': name}
            if description:
                params['DESCRIPTION'] = description
            return self.one.vn.allocate(params)
        except pyone.OneException as e:
            logger.exception('Failed to create network')
            raise OpenNebulaError(e)

    def delete_network(self, network_id):
        """
        Deletes a virtual network.
        :param network_id: Network identifier
        :type network_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vn.delete(network_id)
        except pyone.OneException as e:
            logger.exception('Failed to delete network')
            raise OpenNebulaError(e)

    def list_volumes(self):
        """
        Lists all disk images (volumes).
        :return: Image pool information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.imagepool.info(-2, -1, -1, -1)
        except pyone.OneException as e:
            logger.exception('Failed to list volumes')
            raise OpenNebulaError(e)

    def get_volume(self, volume_id):
        """
        Retrieves information about a specific disk image.
        :param volume_id: Volume identifier
        :type volume_id: int
        :return: Image information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.image.info(volume_id)
        except pyone.OneException as e:
            logger.exception('Failed to get volume info')
            raise OpenNebulaError(e)

    def create_volume(self, name, size, description=None):
        """
        Creates a new disk image (volume).
        :param name: Volume name
        :type name: str
        :param size: Volume size in MB
        :type size: int
        :param description: Volume description
        :type description: str or None
        :return: Image identifier
        :raises OpenNebulaError: If the API call fails
        """
        try:
            params = {'NAME': name, 'SIZE': size}
            if description:
                params['DESCRIPTION'] = description
            return self.one.image.allocate(params)
        except pyone.OneException as e:
            logger.exception('Failed to create volume')
            raise OpenNebulaError(e)

    def delete_volume(self, volume_id):
        """
        Deletes a disk image (volume).
        :param volume_id: Volume identifier
        :type volume_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.image.delete(volume_id)
        except pyone.OneException as e:
            logger.exception('Failed to delete volume')
            raise OpenNebulaError(e)

    def set_group_quota(self, group_id, quota_template):
        """
        Sets the group quota limits.
        :param group_id: Group identifier
        :type group_id: int
        :param quota_template: Quota template
        :type quota_template: dict
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.group.quota(group_id, quota_template)
        except pyone.OneException as e:
            logger.exception('Failed to set group quota')
            raise OpenNebulaError(e)

    def get_group_quota(self, group_id):
        """
        Retrieves the group quota limits.
        :param group_id: Group identifier
        :type group_id: int
        :return: Group quota information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.group.info(group_id).QUOTAS
        except pyone.OneException as e:
            logger.exception('Failed to get group quota')
            raise OpenNebulaError(e)

    def update_network(self, network_id, template):
        """
        Updates a virtual network.
        :param network_id: Network identifier
        :type network_id: int
        :param template: Network template
        :type template: dict
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vn.update(network_id, template, 1)  # 1 = merge
        except pyone.OneException as e:
            logger.exception('Failed to update network')
            raise OpenNebulaError(e)

    def add_ar(self, network_id, ar_template):
        """
        Adds address range to a virtual network.
        :param network_id: Network identifier
        :type network_id: int
        :param ar_template: Address range template
        :type ar_template: dict
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vn.add_ar(network_id, ar_template)
        except pyone.OneException as e:
            logger.exception('Failed to add address range to network')
            raise OpenNebulaError(e)

    def rm_ar(self, network_id, ar_id, force=False):
        """
        Removes address range from a virtual network.
        :param network_id: Network identifier
        :type network_id: int
        :param ar_id: Address range identifier
        :type ar_id: int
        :param force: Force removal
        :type force: bool
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vn.rm_ar(network_id, ar_id, force)
        except pyone.OneException as e:
            logger.exception('Failed to remove address range from network')
            raise OpenNebulaError(e)

    def update_ar(self, network_id, ar_template):
        """
        Updates address range attributes.
        :param network_id: Network identifier
        :type network_id: int
        :param ar_template: Address range template
        :type ar_template: dict
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vn.update_ar(network_id, ar_template)
        except pyone.OneException as e:
            logger.exception('Failed to update address range')
            raise OpenNebulaError(e)

    def reserve_ar(self, network_id, reservation_template):
        """
        Reserves network addresses.
        :param network_id: Network identifier
        :type network_id: int
        :param reservation_template: Reservation template
        :type reservation_template: dict
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vn.reserve(network_id, reservation_template)
        except pyone.OneException as e:
            logger.exception('Failed to reserve address range')
            raise OpenNebulaError(e)

    def create_disk_snapshot(self, vm_id, disk_id, description=None):
        """
        Takes a new snapshot of the disk image.
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param description: Snapshot description
        :type description: str or None
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.disksnapshotcreate(vm_id, disk_id, description or "")
        except pyone.OneException as e:
            logger.exception('Failed to create disk snapshot')
            raise OpenNebulaError(e)

    def delete_disk_snapshot(self, vm_id, disk_id, snapshot_id):
        """
        Deletes a disk snapshot.
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param snapshot_id: Snapshot identifier
        :type snapshot_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.disksnapshotdelete(vm_id, disk_id, snapshot_id)
        except pyone.OneException as e:
            logger.exception('Failed to delete disk snapshot')
            raise OpenNebulaError(e)

    def revert_disk_snapshot(self, vm_id, disk_id, snapshot_id):
        """
        Reverts disk state to a previously taken snapshot.
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param snapshot_id: Snapshot identifier
        :type snapshot_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.disksnapshotrevert(vm_id, disk_id, snapshot_id)
        except pyone.OneException as e:
            logger.exception('Failed to revert disk snapshot')
            raise OpenNebulaError(e)

    def rename_disk_snapshot(self, vm_id, disk_id, snapshot_id, new_name):
        """
        Renames a disk snapshot.
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param snapshot_id: Snapshot identifier
        :type snapshot_id: int
        :param new_name: New snapshot name
        :type new_name: str
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.disksnapshotrename(vm_id, disk_id, snapshot_id, new_name)
        except pyone.OneException as e:
            logger.exception('Failed to rename disk snapshot')
            raise OpenNebulaError(e)

    def resize_disk(self, vm_id, disk_id, size):
        """
        Resizes a disk attached to a VM.
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param size: New disk size
        :type size: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.diskresize(vm_id, disk_id, size)
        except pyone.OneException as e:
            logger.exception('Failed to resize disk')
            raise OpenNebulaError(e)

    def save_disk_as_image(self, vm_id, disk_id, image_name, image_type="", snapshot_id=-1):
        """
        Saves the disk as a new image.
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param image_name: New image name
        :type image_name: str
        :param image_type: Image type
        :type image_type: str
        :param snapshot_id: Snapshot identifier
        :type snapshot_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.disksaveas(vm_id, disk_id, image_name, image_type, snapshot_id)
        except pyone.OneException as e:
            logger.exception('Failed to save disk as image')
            raise OpenNebulaError(e)

    def migrate_vm(self, vm_id, host_id, live=True, enforce=False, ds_id=None, migration_type=0):
        """
        Migrate a VM to a target host.
        
        :param vm_id: VM identifier
        :type vm_id: int
        :param host_id: Destination host identifier
        :type host_id: int
        :param live: Whether to perform a live migration (if possible)
        :type live: bool
        :param enforce: Whether to enforce the migration even if OpenNebula would not migrate it
        :type enforce: bool
        :param ds_id: Optional destination datastore ID
        :type ds_id: int or None
        :param migration_type: Migration type (0: save, 1: poweroff, 2: shutdown)
        :type migration_type: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.migrate(vm_id, host_id, live, enforce, ds_id, migration_type)
        except pyone.OneException as e:
            logger.exception('Failed to migrate VM')
            raise OpenNebulaError(e)

    def disksaveas(self, vm_id, disk_id, image_name, image_type=None, snapshot_id=None):
        """
        Save a disk as a new image.
        
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param image_name: Name for the new image
        :type image_name: str
        :param image_type: Type of the new image (OS, DATABLOCK, CDROM, etc.)
        :type image_type: str or None
        :param snapshot_id: Optional snapshot ID to save from (-1 for current disk state)
        :type snapshot_id: int or None
        :return: New image ID
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.disksaveas(vm_id, disk_id, image_name, image_type or '', snapshot_id or -1)
        except pyone.OneException as e:
            logger.exception('Failed to save disk as image')
            raise OpenNebulaError(e)

    def disksnapshotcreate(self, vm_id, disk_id, description=None):
        """
        Create a new snapshot of a disk.
        
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param description: Optional snapshot description
        :type description: str or None
        :return: New snapshot ID
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.disksnapshotcreate(vm_id, disk_id, description or "")
        except pyone.OneException as e:
            logger.exception('Failed to create disk snapshot')
            raise OpenNebulaError(e)

    def disksnapshotdelete(self, vm_id, disk_id, snapshot_id):
        """
        Delete a disk snapshot.
        
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param snapshot_id: Snapshot identifier to delete
        :type snapshot_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.disksnapshotdelete(vm_id, disk_id, snapshot_id)
        except pyone.OneException as e:
            logger.exception('Failed to delete disk snapshot')
            raise OpenNebulaError(e)

    def disksnapshotrevert(self, vm_id, disk_id, snapshot_id):
        """
        Revert disk state to a previously taken snapshot.
        
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param snapshot_id: Snapshot identifier to revert to
        :type snapshot_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.disksnapshotrevert(vm_id, disk_id, snapshot_id)
        except pyone.OneException as e:
            logger.exception('Failed to revert disk snapshot')
            raise OpenNebulaError(e)

    def disksnapshotrename(self, vm_id, disk_id, snapshot_id, new_name):
        """
        Rename a disk snapshot.
        
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param snapshot_id: Snapshot identifier to rename
        :type snapshot_id: int
        :param new_name: New name for the snapshot
        :type new_name: str
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.disksnapshotrename(vm_id, disk_id, snapshot_id, new_name)
        except pyone.OneException as e:
            logger.exception('Failed to rename disk snapshot')
            raise OpenNebulaError(e)

    def diskresize(self, vm_id, disk_id, size):
        """
        Resize a disk attached to a VM.
        
        :param vm_id: VM identifier
        :type vm_id: int
        :param disk_id: Disk identifier
        :type disk_id: int
        :param size: New disk size in MB
        :type size: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.diskresize(vm_id, disk_id, size)
        except pyone.OneException as e:
            logger.exception('Failed to resize disk')
            raise OpenNebulaError(e)

    def backup_vm(self, vm_id, ds_id, reset=False):
        """
        Take a one-shot backup of a VM.
        
        :param vm_id: VM identifier
        :type vm_id: int
        :param ds_id: Destination datastore identifier for the backup
        :type ds_id: int
        :param reset: Whether to reset VM state after backup (optional)
        :type reset: bool
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.backup(vm_id, ds_id, reset)
        except pyone.OneException as e:
            logger.exception('Failed to backup VM')
            raise OpenNebulaError(e)

    def backup_cancel(self, vm_id):
        """
        Cancel an ongoing backup operation for a VM.
        
        :param vm_id: VM identifier
        :type vm_id: int
        :return: Success status
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.backupcancel(vm_id)
        except pyone.OneException as e:
            logger.exception('Failed to cancel VM backup')
            raise OpenNebulaError(e)

    def restore_vm(self, vm_id, backup_id, in_place=True):
        """
        Restore a VM from a backup.
        
        :param vm_id: VM identifier
        :type vm_id: int
        :param backup_id: Backup image or snapshot identifier
        :type backup_id: int
        :param in_place: Whether to restore in-place (True) or create a new VM (False)
        :type in_place: bool
        :return: Success status or new VM ID if not in-place
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.restore(vm_id, backup_id, in_place)
        except pyone.OneException as e:
            logger.exception('Failed to restore VM from backup')
            raise OpenNebulaError(e)

    def list_templates(self):
        """
        List all available VM templates for deployment.
        
        :return: Template pool information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.templatepool.info(-2, -1, -1, -1)
        except pyone.OneException as e:
            logger.exception('Failed to list templates')
            raise OpenNebulaError(e)

    def list_images(self):
        """
        List all available disk images for VM creation or disk attachment.
        
        :return: Image pool information
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.imagepool.info(-2, -1, -1, -1)
        except pyone.OneException as e:
            logger.exception('Failed to list images')
            raise OpenNebulaError(e)

    def list_hosts(self):
        """
        List all hosts in OpenNebula.
        :return: List of host objects
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.hostpool.info()
        except pyone.OneException as e:
            logger.exception('Failed to list hosts')
            raise OpenNebulaError(e)

    def get_host(self, host_id):
        """
        Get information for a specific host.
        :param host_id: Host identifier
        :type host_id: int
        :return: Host object
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.host.info(host_id)
        except pyone.OneException as e:
            logger.exception('Failed to get host info')
            raise OpenNebulaError(e)

    def create_host(self, name, im_mad, vmm_mad, vnm_mad, cluster_id=None):
        """
        Allocate a new host.
        :param name: Hostname
        :type name: str
        :param im_mad: Information manager driver
        :type im_mad: str
        :param vmm_mad: Virtualization manager driver
        :type vmm_mad: str
        :param vnm_mad: Network manager driver
        :type vnm_mad: str
        :param cluster_id: Optional cluster ID
        :type cluster_id: int or None
        :return: Host ID
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.host.allocate(name, im_mad, vmm_mad, vnm_mad, cluster_id)
        except pyone.OneException as e:
            logger.exception('Failed to create host')
            raise OpenNebulaError(e)

    def delete_host(self, host_id):
        """
        Delete a host by ID.
        :param host_id: Host identifier
        :type host_id: int
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.host.delete(host_id)
        except pyone.OneException as e:
            logger.exception('Failed to delete host')
            raise OpenNebulaError(e)

    def update_host(self, host_id, template, append=True):
        """
        Update a host's template.
        :param host_id: Host identifier
        :type host_id: int
        :param template: Template dict
        :type template: dict
        :param append: Whether to append (True) or replace (False) the template
        :type append: bool
        :raises OpenNebulaError: If the API call fails
        """
        try:
            mode = 1 if append else 0
            return self.one.host.update(host_id, template, mode)
        except pyone.OneException as e:
            logger.exception('Failed to update host')
            raise OpenNebulaError(e)

    def rename_host(self, host_id, new_name):
        """
        Rename a host.
        :param host_id: Host identifier
        :type host_id: int
        :param new_name: New host name
        :type new_name: str
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.host.rename(host_id, new_name)
        except pyone.OneException as e:
            logger.exception('Failed to rename host')
            raise OpenNebulaError(e)

    def set_host_status(self, host_id, status):
        """
        Set the status of a host (enable, disable, offline).
        :param host_id: Host identifier
        :type host_id: int
        :param status: Status string ('enable', 'disable', 'offline')
        :type status: str
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.host.status(host_id, status)
        except pyone.OneException as e:
            logger.exception('Failed to set host status')
            raise OpenNebulaError(e)

    def get_host_monitoring(self, host_id):
        """
        Get monitoring data for a host.
        :param host_id: Host identifier
        :type host_id: int
        :return: Monitoring data
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.host.monitoring(host_id)
        except pyone.OneException as e:
            logger.exception('Failed to get host monitoring')
            raise OpenNebulaError(e)

    def calculate_showback(self, start_month, start_year, end_month, end_year):
        """
        Calculate showback for VMs in a given period.
        :param start_month: Start month (1-12)
        :type start_month: int
        :param start_year: Start year (YYYY)
        :type start_year: int
        :param end_month: End month (1-12)
        :type end_month: int
        :param end_year: End year (YYYY)
        :type end_year: int
        :return: Showback data
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vmpool.calculateshowback(start_month, start_year, end_month, end_year)
        except pyone.OneException as e:
            logger.exception('Failed to calculate showback')
            raise OpenNebulaError(e)

    def attach_nic(self, vm_id, nic_template):
        """
        Attach a NIC to a VM.
        :param vm_id: VM identifier
        :type vm_id: int
        :param nic_template: NIC template dict
        :type nic_template: dict
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.attachnic(vm_id, nic_template)
        except pyone.OneException as e:
            logger.exception('Failed to attach NIC')
            raise OpenNebulaError(e)

    def detach_nic(self, vm_id, nic_id):
        """
        Detach a NIC from a VM.
        :param vm_id: VM identifier
        :type vm_id: int
        :param nic_id: NIC identifier
        :type nic_id: int
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.detachnic(vm_id, nic_id)
        except pyone.OneException as e:
            logger.exception('Failed to detach NIC')
            raise OpenNebulaError(e)

    def update_nic(self, vm_id, nic_id, nic_template):
        """
        Update a NIC on a VM.
        :param vm_id: VM identifier
        :type vm_id: int
        :param nic_id: NIC identifier
        :type nic_id: int
        :param nic_template: NIC template dict
        :type nic_template: dict
        :raises OpenNebulaError: If the API call fails
        """
        try:
            return self.one.vm.updatenic(vm_id, nic_id, nic_template)
        except pyone.OneException as e:
            logger.exception('Failed to update NIC')
            raise OpenNebulaError(e)
    def get_cpu(self, vm_id):
            """
            Returns the CPU-related settings of a virtual machine.

            :param vm_id: Virtual machine identifier
            :type vm_id: string
            """
            try:
                vm = self.one.vm.info(int(vm_id))
            except pyone.OneException as e:
                raise OpenNebulaError(e)
            return vm.TEMPLATE.CPU

    def update_cpu(self, vm_id, spec):
        """
        Updates the CPU-related settings of a virtual machine.

        :param vm_id: Virtual machine identifier
        :type vm_id: string
        :param spec: CPU specification
        :type spec: dict
        """
        try:
            self.one.vm.update(vm_id, "CPU=" + str(spec["count"]), True)
        except pyone.OneException as e:
            raise OpenNebulaError(e)

    def update_memory(self, vm_id, spec):
        """
        Updates the memory-related settings of a virtual machine.

        :param vm_id: Virtual machine identifier
        :type vm_id: string
        :param spec: Memory specification
        :type spec: dict
        """
        try:
            self.one.vm.update(int(vm_id), 'MEMORY = {}'.format(spec['size_MiB']))
        except pyone.OneException as e:
            raise OpenNebulaError(e)
        

    # Add more methods for VM, tenant, network, etc. management as needed