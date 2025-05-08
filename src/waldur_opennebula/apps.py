from django.apps import AppConfig


class OpenNebulaConfig(AppConfig):
    """OpenNebula is a toolkit for building private and public clouds.
    This application adds support for managing OpenNebula deployments -
    tenants, virtual machines, volumes, networks and scheduled actions.
    """

    name = "waldur_opennebula"
    label = "opennebula"
    verbose_name = "OpenNebula"
    service_name = "OpenNebula"    
    
    def ready(self):
        from waldur_core.structure.registry import SupportedServices
        from waldur_core.structure import models as structure_models
        from waldur_core.quotas.fields import TotalQuotaField

        from .backend import OpenNebulaBackend
        SupportedServices.register_backend(OpenNebulaBackend)


        # Register models
        Tenant = self.get_model("OpenNebulaTenant")
        VirtualMachine = self.get_model("OpenNebulaVirtualMachine")
        Network = self.get_model("OpenNebulaNetwork")
        Volume = self.get_model("OpenNebulaVolume")
        ScheduledAction = self.get_model("OpenNebulaScheduledAction")

        # Add quotas for Project
        structure_models.Project.add_quota_field(
            name="opennebula_cpu_count",
            quota_field=TotalQuotaField(
                target_models=[VirtualMachine],
                path_to_scope="project",
                target_field="cpu",
            ),
        )

        structure_models.Project.add_quota_field(
            name="opennebula_ram_size",
            quota_field=TotalQuotaField(
                target_models=[VirtualMachine],
                path_to_scope="project",
                target_field="ram",
            ),
        )

        structure_models.Project.add_quota_field(
            name="opennebula_storage_size",
            quota_field=TotalQuotaField(
                target_models=[Volume],
                path_to_scope="project",
                target_field="size",
            ),
        )

        # Add quotas for Customer
        structure_models.Customer.add_quota_field(
            name="opennebula_cpu_count",
            quota_field=TotalQuotaField(
                target_models=[VirtualMachine],
                path_to_scope="project.customer",
                target_field="cpu",
            ),
        )

        structure_models.Customer.add_quota_field(
            name="opennebula_ram_size",
            quota_field=TotalQuotaField(
                target_models=[VirtualMachine],
                path_to_scope="project.customer",
                target_field="ram",
            ),
        )

        structure_models.Customer.add_quota_field(
            name="opennebula_storage_size",
            quota_field=TotalQuotaField(
                target_models=[Volume],
                path_to_scope="project.customer",
                target_field="size",
            ),
        )

        # Network quotas for Customer
        structure_models.Customer.add_quota_field(
            name="opennebula_network_count",
            quota_field=TotalQuotaField(
                target_models=[Network],
                path_to_scope="project.customer",
                target_field="count",
            ),
        )

        structure_models.Customer.add_quota_field(
            name="opennebula_ip_count",
            quota_field=TotalQuotaField(
                target_models=[Network],
                path_to_scope="project.customer",
                target_field="ip_count",  # Adjust if your field name is different
            ),
        )


        # Register signals if any
        from . import handlers
