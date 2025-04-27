from django.db import models
from waldur_core.core.models import UuidMixin, StateMixin, DescendantMixin, BackendModelMixin
from waldur_core.structure.models import StructureLoggableMixin, ServiceProperty, ServiceSettings, Project


class OpenNebulaTenant(UuidMixin, StateMixin, DescendantMixin, BackendModelMixin, StructureLoggableMixin, models.Model):
    """Represents an OpenNebula project/group/tenant."""
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    service_settings = models.ForeignKey(ServiceSettings, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    backend_id = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("service_settings", "backend_id")
        verbose_name = "OpenNebula Tenant"
        verbose_name_plural = "OpenNebula Tenants"
        ordering = ["name", "created"]

    def __str__(self):
        return self.name


class OpenNebulaVirtualMachine(UuidMixin, StateMixin, DescendantMixin, BackendModelMixin, StructureLoggableMixin, models.Model):
    """Represents an OpenNebula Virtual Machine."""
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    tenant = models.ForeignKey(OpenNebulaTenant, on_delete=models.CASCADE, related_name="vms")
    service_settings = models.ForeignKey(ServiceSettings, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    backend_id = models.CharField(max_length=255, blank=True)
    cpu = models.PositiveIntegerField(default=1)
    ram = models.PositiveIntegerField(default=1024, help_text="RAM in MB")
    disk = models.PositiveIntegerField(default=10, help_text="Disk size in GB")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    progress = models.IntegerField(default=0, help_text="Progress percentage for async operations.")
    error_message = models.TextField(blank=True, null=True, help_text="Last error message, if any.")

    class Meta:
        unique_together = ("service_settings", "backend_id")
        verbose_name = "OpenNebula Virtual Machine"
        verbose_name_plural = "OpenNebula Virtual Machines"
        ordering = ["name", "created"]

    def __str__(self):
        return self.name


class OpenNebulaNetwork(UuidMixin, StateMixin, BackendModelMixin, StructureLoggableMixin, models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    tenant = models.ForeignKey(OpenNebulaTenant, on_delete=models.CASCADE, related_name="networks", null=True, blank=True)
    service_settings = models.ForeignKey(ServiceSettings, on_delete=models.CASCADE)
    backend_id = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    progress = models.IntegerField(default=0, help_text="Progress percentage for async operations.")
    error_message = models.TextField(blank=True, null=True, help_text="Last error message, if any.")

    class Meta:
        unique_together = ("service_settings", "backend_id")
        verbose_name = "OpenNebula Network"
        verbose_name_plural = "OpenNebula Networks"
        ordering = ["name", "created"]

    def __str__(self):
        return self.name


class OpenNebulaVolume(UuidMixin, StateMixin, BackendModelMixin, StructureLoggableMixin, models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    tenant = models.ForeignKey(OpenNebulaTenant, on_delete=models.CASCADE, related_name="volumes", null=True, blank=True)
    service_settings = models.ForeignKey(ServiceSettings, on_delete=models.CASCADE)
    backend_id = models.CharField(max_length=255, blank=True)
    size = models.PositiveIntegerField(default=0, help_text="Size in GB")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    progress = models.IntegerField(default=0, help_text="Progress percentage for async operations.")
    error_message = models.TextField(blank=True, null=True, help_text="Last error message, if any.")

    class Meta:
        unique_together = ("service_settings", "backend_id")
        verbose_name = "OpenNebula Volume"
        verbose_name_plural = "OpenNebula Volumes"
        ordering = ["name", "created"]

    def __str__(self):
        return self.name


class OpenNebulaScheduledAction(models.Model):
    ACTION_CHOICES = [
        ('snapshot', 'Snapshot'),
        ('backup', 'Backup'),
    ]
    vm = models.ForeignKey(OpenNebulaVirtualMachine, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=16, choices=ACTION_CHOICES)
    interval = models.CharField(max_length=16)  # e.g., 'daily', 'weekly', 'cron'
    next_run = models.DateTimeField()
    enabled = models.BooleanField(default=True)
    params = models.JSONField(default=dict, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'OpenNebula Scheduled Action'
        verbose_name_plural = 'OpenNebula Scheduled Actions'
        ordering = ["last_run", "next_run"]

    def __str__(self):
        return f"{self.action_type} for {self.vm} every {self.interval}" 