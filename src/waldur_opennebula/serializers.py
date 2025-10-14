from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from waldur_core.structure import serializers as structure_serializers

from .models import (
    OpenNebulaNetwork,
    OpenNebulaScheduledAction,
    OpenNebulaTenant,
    OpenNebulaVirtualMachine,
    OpenNebulaVolume,
    Project,
    ServiceSettings,
)


class OpenNebulaServiceSerializer(structure_serializers.ServiceOptionsSerializer):
    class Meta:
        secret_fields = ("backend_url", "username", "password")

    backend_url = serializers.CharField(
        label=_("OpenNebula API Endpoint"),
    )

    username = serializers.CharField(
        label=_("OpenNebula Admin Username"),
    )

    password = serializers.CharField(
        label=_("OpenNebula Admin Password"),
    )


class OpenNebulaTenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenNebulaTenant
        fields = "__all__"


class OpenNebulaTenantCreateSerializer(
    structure_serializers.PermissionFieldFilteringMixin, serializers.ModelSerializer
):
    service_settings = serializers.PrimaryKeyRelatedField(
        queryset=ServiceSettings.objects.all()
    )
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())

    class Meta:
        model = OpenNebulaTenant
        fields = ["name", "description", "service_settings", "project"]

    def get_filtered_field_names(self):
        return ("service_settings", "project")

    def get_fields(self):
        fields = super().get_fields()
        service_settings_field = fields.get("service_settings")
        if service_settings_field and not service_settings_field.read_only:
            service_settings_field.queryset = service_settings_field.queryset.filter(
                type="OpenNebula"
            )
        return fields

    def validate(self, attrs):
        attrs = super().validate(attrs)
        service_settings = attrs["service_settings"]
        project = attrs["project"]

        if service_settings.type != "OpenNebula":
            raise serializers.ValidationError(
                {
                    "service_settings": _(
                        "Selected service settings must belong to the OpenNebula plugin."
                    )
                }
            )

        if (
            not service_settings.shared
            and service_settings.customer
            and service_settings.customer != project.customer
        ):
            raise serializers.ValidationError(
                {
                    "service_settings": _(
                        "Service settings must belong to the same organization as the project."
                    )
                }
            )

        return attrs


class OpenNebulaVirtualMachineSerializer(serializers.ModelSerializer):
    state = serializers.ReadOnlyField()
    progress = serializers.ReadOnlyField()
    error_message = serializers.ReadOnlyField()

    class Meta:
        model = OpenNebulaVirtualMachine
        fields = "__all__"


class OpenNebulaNetworkSerializer(serializers.ModelSerializer):
    progress = serializers.ReadOnlyField()
    error_message = serializers.ReadOnlyField()

    class Meta:
        model = OpenNebulaNetwork
        fields = "__all__"


class OpenNebulaVolumeSerializer(serializers.ModelSerializer):
    progress = serializers.ReadOnlyField()
    error_message = serializers.ReadOnlyField()

    class Meta:
        model = OpenNebulaVolume
        fields = (
            "uuid",
            "name",
            "description",
            "tenant",
            "service_settings",
            "backend_id",
            "size",
            "created",
            "modified",
            "progress",
            "error_message",
        )


class OpenNebulaVMCreateSerializer(serializers.Serializer):
    service_settings = serializers.PrimaryKeyRelatedField(
        queryset=ServiceSettings.objects.all()
    )
    template_id = serializers.IntegerField()
    name = serializers.CharField(max_length=128)
    networks = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
    cpu = serializers.FloatField(required=False)
    ram = serializers.IntegerField(required=False)
    disk = serializers.IntegerField(required=False)
    ssh_key = serializers.CharField(required=False, allow_blank=True)
    contextualization = serializers.BooleanField(required=False, default=False)
    extra = serializers.DictField(required=False)

    def validate(self, attrs):
        # Ensure required fields are present
        if not attrs.get("service_settings"):
            raise serializers.ValidationError(
                {"service_settings": "This field is required."}
            )
        if not attrs.get("template_id"):
            raise serializers.ValidationError(
                {"template_id": "This field is required."}
            )
        if not attrs.get("name"):
            raise serializers.ValidationError({"name": "This field is required."})
        if not attrs.get("networks"):
            raise serializers.ValidationError(
                {"networks": "At least one network must be selected."}
            )
        return attrs


class OpenNebulaVMMigrateSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
    host_id = serializers.IntegerField()
    live = serializers.BooleanField(default=True)
    enforce = serializers.BooleanField(default=False)
    ds_id = serializers.IntegerField(required=False, allow_null=True)
    migration_type = serializers.IntegerField(default=0)


class OpenNebulaDiskAttachSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
    image_id = serializers.IntegerField()
    size = serializers.IntegerField(required=False)
    type = serializers.CharField(required=False, allow_blank=True)
    target = serializers.CharField(required=False, allow_blank=True)


class OpenNebulaDiskResizeSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
    disk_id = serializers.IntegerField()
    size = serializers.IntegerField()


class OpenNebulaDiskSaveAsSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
    disk_id = serializers.IntegerField()
    image_name = serializers.CharField()
    image_type = serializers.CharField(required=False, allow_blank=True)
    snapshot_id = serializers.IntegerField(required=False, allow_null=True)


class OpenNebulaVMSnapshotSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
    name = serializers.CharField(max_length=128)


class OpenNebulaVMListSnapshotsSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )


class OpenNebulaBackupCreateSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
    name = serializers.CharField(max_length=128)
    description = serializers.CharField(required=False, allow_blank=True)


class OpenNebulaBackupListSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )


class OpenNebulaRestoreBackupSerializer(serializers.Serializer):
    backup_id = serializers.CharField()
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all(), required=False
    )
    in_place = serializers.BooleanField(default=True)
    new_vm_name = serializers.CharField(required=False, allow_blank=True)


class OpenNebulaFloatingIPAssignSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
    network_id = serializers.IntegerField()
    ip_address = serializers.CharField(required=False, allow_blank=True)


class OpenNebulaFloatingIPReleaseSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
    ip_address = serializers.CharField()


class OpenNebulaMarketplaceOfferingSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    template_id = serializers.IntegerField()
    image_id = serializers.IntegerField(required=False)
    cpu = serializers.FloatField(required=False)
    ram = serializers.IntegerField(required=False)
    disk = serializers.IntegerField(required=False)
    price = serializers.FloatField(required=False)
    category = serializers.CharField(required=False, allow_blank=True)
    extra = serializers.DictField(required=False)


class OpenNebulaVMMonitoringSerializer(serializers.Serializer):
    cpu = serializers.FloatField()
    memory = serializers.FloatField()
    disk = serializers.FloatField()
    net_rx = serializers.FloatField()
    net_tx = serializers.FloatField()
    timestamp = serializers.DateTimeField()


class OpenNebulaQuotaSerializer(serializers.Serializer):
    vms = serializers.IntegerField()
    cpu = serializers.FloatField()
    ram = serializers.IntegerField()
    storage = serializers.IntegerField()


class OpenNebulaScheduledActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenNebulaScheduledAction
        fields = "__all__"


class OpenNebulaNetworkAttachSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
    network_id = serializers.IntegerField()
    ip_address = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    model = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Network card model, e.g., 'virtio'",
    )


class OpenNebulaNetworkReleaseSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
    nic_id = serializers.IntegerField(help_text="ID of the network interface to detach")


class OpenNebulaNetworkUpdateSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
    nic_id = serializers.IntegerField(help_text="ID of the network interface to update")
    security_groups = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Security groups to apply to the interface",
    )
    network_qos = serializers.DictField(
        required=False,
        allow_null=True,
        help_text="Quality of Service settings for the network interface",
    )
    model = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Network card model, e.g., 'virtio'",
    )


class OpenNebulaNetworkListSerializer(serializers.Serializer):
    vm = serializers.PrimaryKeyRelatedField(
        queryset=OpenNebulaVirtualMachine.objects.all()
    )
