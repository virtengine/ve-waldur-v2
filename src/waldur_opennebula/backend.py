from waldur_core.structure.backend import ServiceBackend
from waldur_core.structure.exceptions import ServiceBackendError
from .client import OpenNebulaClient
from .models import OpenNebulaTenant, OpenNebulaVirtualMachine, OpenNebulaNetwork, OpenNebulaVolume
import logging

logger = logging.getLogger(__name__)


class OpenNebulaBackendError(ServiceBackendError):
    pass


class OpenNebulaBackend(ServiceBackend):
    """Waldur interface to OpenNebula API using pyone."""

    def __init__(self, settings):
        super().__init__(settings)
        self.settings = settings  # Explicitly assign settings for linter compliance
        self.client = OpenNebulaClient(
            endpoint=settings.options.get("api_url"),
            username=settings.options.get("username"),
            password=settings.options.get("password"),
        )


    def ping(self, raise_exception=False):
        """
        Check connection to OpenNebula by retrieving the system version.
        :param raise_exception: Raise exception if ping fails
        :type raise_exception: bool
        :return: True if successful, False otherwise
        :raises OpenNebulaBackendError: If ping fails and raise_exception is True
        """
        try:
            version = self.client.get_version()
            return True
        except Exception as e:
            logger.exception('Failed to ping OpenNebula backend')
            if raise_exception:
                raise OpenNebulaBackendError(e)
            return False

    def pull_tenants(self):
        """
        Pull all groups/projects from OpenNebula and update/create local DB entries.
        :return: List of group objects
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            groups = self.client.list_groups()
            for group in groups:
                obj, _ = OpenNebulaTenant.objects.update_or_create(
                    backend_id=str(group.ID),
                    defaults={
                        'name': group.NAME,
                        'description': getattr(group, 'DESCRIPTION', ''),
                        'service_settings': self.settings,
                        'project': None,  # Project mapping logic can be added
                    },
                )
                obj.set_ok()
                obj.save(update_fields=['state'])
            return groups
        except Exception as e:
            logger.exception('Failed to pull tenants from OpenNebula')
            raise OpenNebulaBackendError(e)

    def create_tenant(self, name, description=None):
        """
        Create a group/project in OpenNebula and a local DB entry.
        :param name: Tenant name
        :type name: str
        :param description: Tenant description
        :type description: str or None
        :return: OpenNebulaTenant instance
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            group_id = self.client.create_group(name, description)
            group_info = self.client.get_group(group_id)
            tenant = OpenNebulaTenant.objects.create(
                backend_id=str(group_id),
                name=name,
                description=description or '',
                service_settings=self.settings,
                project=None,
            )
            tenant.set_ok()
            tenant.save(update_fields=['state'])
            return tenant
        except Exception as e:
            logger.exception('Failed to create tenant in OpenNebula')
            raise OpenNebulaBackendError(e)

    def delete_tenant(self, tenant):
        """
        Delete group in OpenNebula and schedule local deletion.
        :param tenant: OpenNebulaTenant instance
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            self.client.delete_group(tenant.backend_id)
            tenant.schedule_deleting()
            tenant.save(update_fields=['state'])
            tenant.delete()
        except Exception as e:
            logger.exception('Failed to delete tenant in OpenNebula')
            raise OpenNebulaBackendError(e)

    def pull_vms(self, tenant=None):
        """
        Pull all VMs from OpenNebula and update/create local DB entries.
        :param tenant: Optional OpenNebulaTenant instance
        :return: List of VM objects
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            vms = self.client.list_vms()
            for vm in vms:
                obj, _ = OpenNebulaVirtualMachine.objects.update_or_create(
                    backend_id=str(vm.ID),
                    defaults={
                        'name': vm.NAME,
                        'cpu': int(vm.TEMPLATE.CPU) if hasattr(vm.TEMPLATE, 'CPU') else 1,
                        'ram': int(vm.TEMPLATE.MEMORY) if hasattr(vm.TEMPLATE, 'MEMORY') else 1024,
                        'disk': 10,  # Disk size extraction can be improved
                        'tenant': tenant,
                        'service_settings': self.settings,
                        'project': tenant.project if tenant else None,
                    },
                )
                obj.set_ok()
                obj.save(update_fields=['state'])
            return vms
        except Exception as e:
            logger.exception('Failed to pull VMs from OpenNebula')
            raise OpenNebulaBackendError(e)

    def create_vm(self, tenant, name, template_id, cpu=1, ram=1024, disk=10):
        """
        Create a VM in OpenNebula and a local DB entry.
        :param tenant: OpenNebulaTenant instance
        :param name: VM name
        :param template_id: Template ID
        :param cpu: Number of CPUs
        :param ram: RAM in MB
        :param disk: Disk size in GB
        :return: OpenNebulaVirtualMachine instance
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            extra = {'CPU': cpu, 'MEMORY': ram}
            vm_id = self.client.create_vm(template_id, name=name, extra=extra)
            vm_info = self.client.get_vm(vm_id)
            vm = OpenNebulaVirtualMachine.objects.create(
                backend_id=str(vm_id),
                name=name,
                cpu=cpu,
                ram=ram,
                disk=disk,
                tenant=tenant,
                service_settings=self.settings,
                project=tenant.project,
            )
            vm.set_ok()
            vm.save(update_fields=['state'])
            return vm
        except Exception as e:
            logger.exception('Failed to create VM in OpenNebula')
            raise OpenNebulaBackendError(e)

    def delete_vm(self, vm):
        """
        Delete a VM in OpenNebula and schedule local deletion.
        :param vm: OpenNebulaVirtualMachine instance
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            self.client.delete_vm(vm.backend_id)
            vm.schedule_deleting()
            vm.save(update_fields=['state'])
            vm.delete()
        except Exception as e:
            logger.exception('Failed to delete VM in OpenNebula')
            raise OpenNebulaBackendError(e)

    def start_vm(self, vm):
        """
        Start a VM in OpenNebula.
        :param vm: OpenNebulaVirtualMachine instance
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            self.client.start_vm(vm.backend_id)
            vm.set_ok()
            vm.save(update_fields=['state'])
        except Exception as e:
            logger.exception('Failed to start VM in OpenNebula')
            raise OpenNebulaBackendError(e)

    def stop_vm(self, vm):
        """
        Stop (power off) a VM in OpenNebula.
        :param vm: OpenNebulaVirtualMachine instance
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            self.client.stop_vm(vm.backend_id)
            vm.set_ok()
            vm.save(update_fields=['state'])
        except Exception as e:
            logger.exception('Failed to stop VM in OpenNebula')
            raise OpenNebulaBackendError(e)

    def pull_volumes(self, tenant=None):
        """
        Pull all volumes from OpenNebula and update/create local DB entries.
        :param tenant: Optional OpenNebulaTenant instance
        :return: List of volume objects
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            volumes = self.client.list_volumes()
            for vol in volumes:
                obj, _ = OpenNebulaVolume.objects.update_or_create(
                    backend_id=str(vol.ID),
                    defaults={
                        'name': vol.NAME,
                        'description': getattr(vol, 'DESCRIPTION', ''),
                        'tenant': tenant,
                        'service_settings': self.settings,
                        'size': int(getattr(vol, 'SIZE', 0)),
                    },
                )
                obj.set_ok()
                obj.save(update_fields=['state'])
            return volumes
        except Exception as e:
            logger.exception('Failed to pull volumes from OpenNebula')
            raise OpenNebulaBackendError(e)

    def create_volume(self, tenant, name, size, description=None):
        """
        Create a volume in OpenNebula and a local DB entry.
        :param tenant: OpenNebulaTenant instance
        :param name: Volume name
        :param size: Volume size
        :param description: Volume description
        :return: OpenNebulaVolume instance
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            vol_id = self.client.create_volume(name, size, description)
            vol_info = self.client.get_volume(vol_id)
            volume = OpenNebulaVolume.objects.create(
                backend_id=str(vol_id),
                name=name,
                description=description or '',
                tenant=tenant,
                service_settings=self.settings,
                size=size,
            )
            volume.set_ok()
            volume.save(update_fields=['state'])
            return volume
        except Exception as e:
            logger.exception('Failed to create volume in OpenNebula')
            raise OpenNebulaBackendError(e)

    def delete_volume(self, volume):
        """
        Delete a volume in OpenNebula and schedule local deletion.
        :param volume: OpenNebulaVolume instance
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            self.client.delete_volume(volume.backend_id)
            volume.schedule_deleting()
            volume.save(update_fields=['state'])
            volume.delete()
        except Exception as e:
            logger.exception('Failed to delete volume in OpenNebula')
            raise OpenNebulaBackendError(e)

    def set_tenant_quota(self, tenant, quota_template):
        """
        Set quota limits for a tenant (group) in OpenNebula.
        
        :param tenant: OpenNebulaTenant instance
        :type tenant: OpenNebulaTenant
        :param quota_template: Quota template with limits to set
        :type quota_template: dict
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            return self.client.set_group_quota(int(tenant.backend_id), quota_template)
        except Exception as e:
            logger.exception('Failed to set tenant quota in OpenNebula')
            raise OpenNebulaBackendError(e)

    def get_tenant_quota(self, tenant):
        """
        Get current quota limits for a tenant (group) from OpenNebula.
        
        :param tenant: OpenNebulaTenant instance
        :type tenant: OpenNebulaTenant
        :return: Quota information dictionary
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            return self.client.get_group_quota(int(tenant.backend_id))
        except Exception as e:
            logger.exception('Failed to get tenant quota from OpenNebula')
            raise OpenNebulaBackendError(e)

    def reboot_vm(self, vm):
        """
        Reboot a virtual machine.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.reboot_vm(vm.backend_id)
            # Update VM state in the database
            vm.set_ok()
            vm.save(update_fields=['state'])
            return result
        except Exception as e:
            logger.exception('Failed to reboot VM in OpenNebula')
            raise OpenNebulaBackendError(e)

    def resize_vm(self, vm, cpu=None, ram=None):
        """
        Resize a virtual machine's CPU and/or RAM.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param cpu: New CPU value (number of vCPUs)
        :type cpu: float or None
        :param ram: New RAM value in MB
        :type ram: int or None
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.resize_vm(vm.backend_id, cpu=cpu, ram=ram)
            
            # Update VM resource values in the database
            if cpu is not None:
                vm.cpu = cpu
            if ram is not None:
                vm.ram = ram
                
            vm.set_ok()
            vm.save(update_fields=['cpu', 'ram', 'state'])
            return result
        except Exception as e:
            logger.exception('Failed to resize VM in OpenNebula')
            raise OpenNebulaBackendError(e)

    def attach_disk(self, vm, volume):
        """
        Attach a disk volume to a virtual machine.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param volume: OpenNebulaVolume instance to attach
        :type volume: OpenNebulaVolume
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            # Create a disk template with the volume ID
            disk_template = {
                'IMAGE_ID': volume.backend_id,
                'DEV_PREFIX': 'vd',  # This is a typical device prefix, but might need adjustment
            }
            
            result = self.client.attach_disk(vm.backend_id, disk_template)
            
            # Update the relationship between VM and volume
            # Note: You might need a separate model for VM-volume relationships
            # or add a field to the volume model to track attachment status
            
            # Update states
            vm.set_ok()
            vm.save(update_fields=['state'])
            volume.set_ok()
            volume.save(update_fields=['state'])
            
            return result
        except Exception as e:
            logger.exception('Failed to attach disk to VM in OpenNebula')
            raise OpenNebulaBackendError(e)

    def detach_disk(self, vm, disk_id):
        """
        Detach a disk from a virtual machine.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param disk_id: ID of the disk to detach
        :type disk_id: int
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.detach_disk(vm.backend_id, disk_id)
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            # If you have a relationship model or field for volume attachment,
            # you would update it here
            
            return result
        except Exception as e:
            logger.exception('Failed to detach disk from VM in OpenNebula')
            raise OpenNebulaBackendError(e)

    def snapshot_vm(self, vm, name):
        """
        Create a snapshot of a virtual machine.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param name: Name for the snapshot
        :type name: str
        :return: Snapshot ID
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            snapshot_id = self.client.snapshot_vm(vm.backend_id, name)
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            # You might want to create a DB entry for the snapshot
            # if you have a model for VM snapshots
            
            return snapshot_id
        except Exception as e:
            logger.exception('Failed to create VM snapshot in OpenNebula')
            raise OpenNebulaBackendError(e)

    def restore_vm_snapshot(self, vm, snapshot_id):
        """
        Restore a virtual machine from a snapshot.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param snapshot_id: ID of the snapshot to restore
        :type snapshot_id: int
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.restore_vm_snapshot(vm.backend_id, snapshot_id)
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            return result
        except Exception as e:
            logger.exception('Failed to restore VM snapshot in OpenNebula')
            raise OpenNebulaBackendError(e)

    def get_console(self, vm):
        """
        Get console connection information for a virtual machine.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :return: Console connection information
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            return self.client.get_console(vm.backend_id)
        except Exception as e:
            logger.exception('Failed to get VM console in OpenNebula')
            raise OpenNebulaBackendError(e)

    def update_network(self, network, template):
        """
        Update a virtual network's configuration.
        
        :param network: OpenNebulaNetwork instance
        :type network: OpenNebulaNetwork
        :param template: Network configuration template
        :type template: dict
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.update_network(network.backend_id, template)
            
            # Update network state
            network.set_ok()
            network.save(update_fields=['state'])
            
            return result
        except Exception as e:
            logger.exception('Failed to update network in OpenNebula')
            raise OpenNebulaBackendError(e)

    def add_ar(self, network, ar_template):
        """
        Add an address range to a virtual network.
        
        :param network: OpenNebulaNetwork instance
        :type network: OpenNebulaNetwork
        :param ar_template: Address range template
        :type ar_template: dict
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.add_ar(network.backend_id, ar_template)
            
            # Update network state
            network.set_ok()
            network.save(update_fields=['state'])
            
            return result
        except Exception as e:
            logger.exception('Failed to add address range to network in OpenNebula')
            raise OpenNebulaBackendError(e)

    def rm_ar(self, network, ar_id, force=False):
        """
        Remove an address range from a virtual network.
        
        :param network: OpenNebulaNetwork instance
        :type network: OpenNebulaNetwork
        :param ar_id: Address range ID to remove
        :type ar_id: int
        :param force: Force removal even if in use
        :type force: bool
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.rm_ar(network.backend_id, ar_id, force)
            
            # Update network state
            network.set_ok()
            network.save(update_fields=['state'])
            
            return result
        except Exception as e:
            logger.exception('Failed to remove address range from network in OpenNebula')
            raise OpenNebulaBackendError(e)

    def update_ar(self, network, ar_template):
        """
        Update an address range in a virtual network.
        
        :param network: OpenNebulaNetwork instance
        :type network: OpenNebulaNetwork
        :param ar_template: Address range template with updates
        :type ar_template: dict
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.update_ar(network.backend_id, ar_template)
            
            # Update network state
            network.set_ok()
            network.save(update_fields=['state'])
            
            return result
        except Exception as e:
            logger.exception('Failed to update address range in network in OpenNebula')
            raise OpenNebulaBackendError(e)

    def reserve_ar(self, network, reservation_template):
        """
        Reserve addresses from a virtual network.
        
        :param network: OpenNebulaNetwork instance
        :type network: OpenNebulaNetwork
        :param reservation_template: Reservation configuration template
        :type reservation_template: dict
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.reserve_ar(network.backend_id, reservation_template)
            
            # Update network state
            network.set_ok()
            network.save(update_fields=['state'])
            
            return result
        except Exception as e:
            logger.exception('Failed to reserve address range in OpenNebula')
            raise OpenNebulaBackendError(e)

    def create_disk_snapshot(self, vm, disk_id, description=None):
        """
        Create a new snapshot of a disk image.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param disk_id: ID of the disk to snapshot
        :type disk_id: int
        :param description: Optional snapshot description
        :type description: str or None
        :return: Snapshot ID
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            snapshot_id = self.client.create_disk_snapshot(vm.backend_id, disk_id, description)
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            # You might want to create a DB entry for the disk snapshot
            # if you have a model for disk snapshots
            
            return snapshot_id
        except Exception as e:
            logger.exception('Failed to create disk snapshot in OpenNebula')
            raise OpenNebulaBackendError(e)

    def delete_disk_snapshot(self, vm, disk_id, snapshot_id):
        """
        Delete a disk snapshot.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param disk_id: ID of the disk
        :type disk_id: int
        :param snapshot_id: ID of the snapshot to delete
        :type snapshot_id: int
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.delete_disk_snapshot(vm.backend_id, disk_id, snapshot_id)
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            # If you have a disk snapshot model, you would delete the DB entry here
            
            return result
        except Exception as e:
            logger.exception('Failed to delete disk snapshot in OpenNebula')
            raise OpenNebulaBackendError(e)

    def revert_disk_snapshot(self, vm, disk_id, snapshot_id):
        """
        Revert disk state to a previously taken snapshot.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param disk_id: ID of the disk
        :type disk_id: int
        :param snapshot_id: ID of the snapshot to revert to
        :type snapshot_id: int
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.revert_disk_snapshot(vm.backend_id, disk_id, snapshot_id)
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            return result
        except Exception as e:
            logger.exception('Failed to revert disk snapshot in OpenNebula')
            raise OpenNebulaBackendError(e)

    def rename_disk_snapshot(self, vm, disk_id, snapshot_id, new_name):
        """
        Rename a disk snapshot.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param disk_id: ID of the disk
        :type disk_id: int
        :param snapshot_id: ID of the snapshot to rename
        :type snapshot_id: int
        :param new_name: New name for the snapshot
        :type new_name: str
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.rename_disk_snapshot(vm.backend_id, disk_id, snapshot_id, new_name)
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            # If you have a disk snapshot model, you would update the name here
            
            return result
        except Exception as e:
            logger.exception('Failed to rename disk snapshot in OpenNebula')
            raise OpenNebulaBackendError(e)

    def resize_disk(self, vm, disk_id, size):
        """
        Resize a disk attached to a virtual machine.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param disk_id: ID of the disk to resize
        :type disk_id: int
        :param size: New disk size in MB
        :type size: int
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.resize_disk(vm.backend_id, disk_id, size)
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            # If you track disk sizes in your database, you would update that here
            
            return result
        except Exception as e:
            logger.exception('Failed to resize disk in OpenNebula')
            raise OpenNebulaBackendError(e)

    def save_disk_as_image(self, vm, disk_id, image_name, image_type="", snapshot_id=-1):
        """
        Save a disk as a new image in OpenNebula.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param disk_id: ID of the disk to save
        :type disk_id: int
        :param image_name: Name for the new image
        :type image_name: str
        :param image_type: Type of the image (default: empty string)
        :type image_type: str
        :param snapshot_id: ID of the snapshot to use (-1 for current state)
        :type snapshot_id: int
        :return: New image ID
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            image_id = self.client.save_disk_as_image(vm.backend_id, disk_id, image_name, image_type, snapshot_id)
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            # You might want to create a new volume entry in the DB for the new image
            # This would depend on your application's logic for handling newly created images
            
            return image_id
        except Exception as e:
            logger.exception('Failed to save disk as image in OpenNebula')
            raise OpenNebulaBackendError(e)

    def pull_networks(self, tenant=None):
        # Pull all networks from OpenNebula and update/create local DB entries
        networks = self.client.list_networks()
        for net in networks:
            obj, _ = OpenNebulaNetwork.objects.update_or_create(
                backend_id=str(net.ID),
                defaults={
                    'name': net.NAME,
                    'description': getattr(net, 'DESCRIPTION', ''),
                    'tenant': tenant,
                    'service_settings': self.settings,
                },
            )
            obj.set_ok()
            obj.save(update_fields=['state'])
        return networks

    def create_network(self, tenant, name, description=None):
        # Create a virtual network in OpenNebula and a local DB entry
        net_id = self.client.create_network(name, description)
        net_info = self.client.get_network(net_id)
        network = OpenNebulaNetwork.objects.create(
            backend_id=str(net_id),
            name=name,
            description=description or '',
            tenant=tenant,
            service_settings=self.settings,
        )
        network.set_ok()
        network.save(update_fields=['state'])
        return network

    def delete_network(self, network):
        # Delete a virtual network in OpenNebula and remove the local DB entry
        self.client.delete_network(network.backend_id)
        network.schedule_deleting()
        network.save(update_fields=['state'])
        network.delete()

    def migrate_vm(self, vm, host_id, live=True, enforce=False, ds_id=None, migration_type=0):
        """Migrate a VM to a target host."""
        return self.client.migrate_vm(vm.backend_id, host_id, live, enforce, ds_id, migration_type)

    def backup_vm(self, vm, ds_id, reset: bool = False):
        """
        Take a one-shot backup of a VM.
        :param vm: OpenNebulaVirtualMachine instance
        :param ds_id: Datastore ID
        :param reset: Boolean, whether to reset the backup
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            safe_reset = reset if reset is not None else False
            return self.client.backup_vm(vm.backend_id, ds_id, bool(safe_reset))
        except Exception as e:
            logger.exception('Failed to backup VM in OpenNebula')
            raise OpenNebulaBackendError(e)

    def backup_cancel(self, vm):
        """Cancel an ongoing backup operation for a VM."""
        return self.client.backup_cancel(vm.backend_id)

    def restore_vm(self, vm, backup_id, in_place=True):
        """
        Restore a VM from backup.
        :param vm: OpenNebulaVirtualMachine instance
        :param backup_id: Backup ID
        :param in_place: Boolean, whether to restore in place
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            if vm is None:
                raise OpenNebulaBackendError('VM instance is required for restore_vm.')
            return self.client.restore_vm(vm.backend_id, backup_id, in_place)
        except Exception as e:
            logger.exception('Failed to restore VM in OpenNebula')
            raise OpenNebulaBackendError(e)

    def list_snapshots(self, vm):
        client = OpenNebulaClient(vm.service_settings.backend_url, vm.service_settings.username, vm.service_settings.password)
        info = client.get_vm(vm.backend_id)
        # Assume info.SNAPSHOTS.SNAPSHOT is a list of snapshot objects
        snapshots = getattr(getattr(info, 'SNAPSHOTS', None), 'SNAPSHOT', [])
        return [
            {
                'id': s.ID,
                'name': s.NAME,
                'date': getattr(s, 'DATE', None),
                'active': getattr(s, 'ACTIVE', None),
            }
            for s in snapshots
        ]

    def create_snapshot(self, vm, name):
        client = OpenNebulaClient(vm.service_settings.backend_url, vm.service_settings.username, vm.service_settings.password)
        return client.snapshot_vm(vm.backend_id, name)

    def list_backups(self, vm):
        client = OpenNebulaClient(vm.service_settings.backend_url, vm.service_settings.username, vm.service_settings.password)
        # This is a placeholder; actual implementation depends on OpenNebula backup API
        # For now, return a list of backup dicts
        info = client.get_vm(vm.backend_id)
        backups = getattr(getattr(info, 'BACKUPS', None), 'BACKUP', [])
        return [
            {
                'id': b.ID,
                'name': b.NAME,
                'date': getattr(b, 'DATE', None),
                'type': getattr(b, 'TYPE', None),
                'state': getattr(b, 'STATE', None),
            }
            for b in backups
        ]

    def create_backup(self, vm, name, description=None):
        client = OpenNebulaClient(vm.service_settings.backend_url, vm.service_settings.username, vm.service_settings.password)
        # This is a placeholder; actual implementation depends on OpenNebula backup API
        return client.backup_vm(vm.backend_id, name, description)

    def restore_backup(self, backup_id, vm=None, in_place=True, new_vm_name=None):
        """
        Restore a backup to a VM or as a new VM.
        :param backup_id: Backup ID
        :param vm: OpenNebulaVirtualMachine instance or None
        :param in_place: Boolean, whether to restore in place
        :param new_vm_name: Name for the new VM if not restoring in place
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            if vm and in_place:
                return self.client.restore_vm(vm.backend_id, backup_id, in_place=True)
            elif not in_place and new_vm_name:
                # OpenNebulaClient.restore_vm does not support new_vm_name; not implemented
                raise NotImplementedError('Restoring backup as a new VM with a custom name is not supported by OpenNebulaClient.restore_vm.')
            else:
                raise OpenNebulaBackendError('Invalid parameters for restore_backup: either vm and in_place, or new_vm_name must be provided.')
        except Exception as e:
            logger.exception('Failed to restore backup in OpenNebula')
            raise OpenNebulaBackendError(e)

    def list_marketplace_offerings(self):
        client = OpenNebulaClient(self.settings.options.get("api_url"), self.settings.options.get("username"), self.settings.options.get("password"))
        templates = client.list_templates()
        images = client.list_images()
        # Aggregate templates/images into offering dicts
        offerings = []
        for t in getattr(templates, 'VMTEMPLATE', []):
            offering = {
                'id': t.ID,
                'name': t.NAME,
                'description': getattr(t, 'DESCRIPTION', ''),
                'template_id': t.ID,
                'cpu': getattr(t.TEMPLATE, 'CPU', None),
                'ram': getattr(t.TEMPLATE, 'MEMORY', None),
                'disk': getattr(t.TEMPLATE, 'DISK_SIZE', None),
                'category': getattr(t, 'CATEGORY', ''),
                'extra': {},
            }
            # Optionally, link to an image
            if hasattr(t.TEMPLATE, 'IMAGE_ID'):
                offering['image_id'] = t.TEMPLATE.IMAGE_ID
            offerings.append(offering)
        return offerings

    def get_vm_monitoring(self, vm):
        # Use OpenNebula XML-RPC: one.vm.monitoring
        return self.client.one.vm.monitoring(vm.backend_id)

    def get_vmpool_monitoring(self):
        # Use OpenNebula XML-RPC: one.vmpool.monitoring
        return self.client.one.vmpool.monitoring(-2, -1, -1, -1)

    def get_group_quota(self, tenant):
        info = self.client.get_group(tenant.backend_id)
        return getattr(info, 'QUOTAS', {})

    # Add methods for tenant and VM management, following OpenStack backend as a guide
    
    def attach_nic(self, vm, network_id, ip=None, model=None):
        """
        Attach a new network interface to a virtual machine.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param network_id: ID of the network to connect to
        :type network_id: int or str
        :param ip: Optional specific IP address to assign
        :type ip: str or None
        :param model: Optional NIC model (e.g., 'virtio')
        :type model: str or None
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            # Build NIC template
            nic_template = {'NETWORK_ID': int(network_id)}
            
            # Add optional parameters if provided
            if ip:
                nic_template['IP'] = ip
            if model:
                nic_template['MODEL'] = model
                
            result = self.client.attach_nic(int(vm.backend_id), nic_template)
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            return result
        except Exception as e:
            logger.exception('Failed to attach NIC to VM in OpenNebula')
            raise OpenNebulaBackendError(f"Failed to attach NIC: {str(e)}")
    
    def detach_nic(self, vm, nic_id):
        """
        Detach a network interface from a virtual machine.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param nic_id: ID of the NIC to detach
        :type nic_id: int or str
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            result = self.client.detach_nic(int(vm.backend_id), int(nic_id))
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            return result
        except Exception as e:
            logger.exception('Failed to detach NIC from VM in OpenNebula')
            raise OpenNebulaBackendError(f"Failed to detach NIC: {str(e)}")
    
    def update_nic(self, vm, nic_id, **kwargs):
        """
        Update a network interface on a virtual machine.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :param nic_id: ID of the NIC to update
        :type nic_id: int or str
        :param kwargs: Parameters to update (e.g., security_groups, network_qos, etc.)
        :return: Success status
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            # Build NIC template with provided parameters
            nic_template = {}
            
            # Map common parameters to OpenNebula NIC attributes
            if 'security_groups' in kwargs:
                nic_template['SECURITY_GROUPS'] = kwargs['security_groups']
            if 'network_qos' in kwargs:
                nic_template['INBOUND_AVG_BW'] = kwargs['network_qos'].get('inbound_avg_bw')
                nic_template['INBOUND_PEAK_BW'] = kwargs['network_qos'].get('inbound_peak_bw')
                nic_template['OUTBOUND_AVG_BW'] = kwargs['network_qos'].get('outbound_avg_bw')
                nic_template['OUTBOUND_PEAK_BW'] = kwargs['network_qos'].get('outbound_peak_bw')
            if 'model' in kwargs:
                nic_template['MODEL'] = kwargs['model']
            
            # Add any other parameters directly
            for key, value in kwargs.items():
                if key not in ['security_groups', 'network_qos', 'model'] and value is not None:
                    nic_template[key.upper()] = value
            
            # Only proceed if we have parameters to update
            if not nic_template:
                logger.warning('No parameters provided for NIC update')
                return False
                
            result = self.client.update_nic(int(vm.backend_id), int(nic_id), nic_template)
            
            # Update VM state
            vm.set_ok()
            vm.save(update_fields=['state'])
            
            return result
        except Exception as e:
            logger.exception('Failed to update NIC on VM in OpenNebula')
            raise OpenNebulaBackendError(f"Failed to update NIC: {str(e)}")
    
    def list_nics(self, vm):
        """
        List all network interfaces attached to a virtual machine.
        
        :param vm: OpenNebulaVirtualMachine instance
        :type vm: OpenNebulaVirtualMachine
        :return: List of NIC information dictionaries
        :raises OpenNebulaBackendError: If the operation fails
        """
        try:
            # Get the VM info which contains NIC data
            vm_info = self.client.get_vm(int(vm.backend_id))
            
            # Extract NIC information
            nics = []
            if hasattr(vm_info.TEMPLATE, 'NIC'):
                # Handle both single NIC and multiple NICs
                nic_data = vm_info.TEMPLATE.NIC
                if isinstance(nic_data, list):
                    for nic in nic_data:
                        nics.append({
                            'id': getattr(nic, 'NIC_ID', None),
                            'network_id': getattr(nic, 'NETWORK_ID', None),
                            'network': getattr(nic, 'NETWORK', None),
                            'mac': getattr(nic, 'MAC', None),
                            'ip': getattr(nic, 'IP', None),
                            'model': getattr(nic, 'MODEL', None),
                            'security_groups': getattr(nic, 'SECURITY_GROUPS', None),
                        })
                else:
                    nics.append({
                        'id': getattr(nic_data, 'NIC_ID', None),
                        'network_id': getattr(nic_data, 'NETWORK_ID', None),
                        'network': getattr(nic_data, 'NETWORK', None),
                        'mac': getattr(nic_data, 'MAC', None),
                        'ip': getattr(nic_data, 'IP', None),
                        'model': getattr(nic_data, 'MODEL', None),
                        'security_groups': getattr(nic_data, 'SECURITY_GROUPS', None),
                    })
            
            return nics
        except Exception as e:
            logger.exception('Failed to list NICs for VM in OpenNebula')
            raise OpenNebulaBackendError(f"Failed to list NICs: {str(e)}")