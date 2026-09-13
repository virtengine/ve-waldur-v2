from django.db import migrations
from django.utils import timezone

# Mastermind no longer talks to Azure: the waldur_azure and marketplace_azure
# apps are gone, and the site agent's Azure plugin manages the VMs from the
# provider site instead. Dropping the offerings would drop the running VMs from
# Waldur, so they are handed to the agent instead: each Azure.VirtualMachine
# offering becomes a Site Agent offering, and its resources, orders, plans and
# invoice items stay exactly as they are. An agent configured with the
# offering's UUID then manages the existing resources by backend_id, with no
# import or recreate.
#
# The agent addresses a VM by its full Azure resource ID. VMs mastermind created
# already store it; imported VMs stored only the VM name (and their resource
# group only its name), so the ID is rebuilt here from what the removed app left
# behind. Its models no longer exist, so its tables are read with raw SQL, and
# only when they exist: fresh installs never had them.
#
# Rows are changed through historical models and queryset updates, so no signal
# handlers run. Generic pointers at waldur_azure content types are cleared by
# hand, because the database does not enforce GenericForeignKey cascades.
#
# Irreversible: reversing restores the migration record, not the old offering
# types or backend ids.

VM_OFFERING_TYPE = "Azure.VirtualMachine"
SQL_SERVER_OFFERING_TYPE = "Azure.SQLServer"
# Frozen copy of marketplace.enums.SITE_AGENT_OFFERING as of this migration.
SITE_AGENT_OFFERING_TYPE = "Marketplace.Slurm"

# Pausing and downscaling are how the agent deallocates a VM and later starts it
# again; without them those actions are not offered on the resources.
AGENT_PLUGIN_OPTIONS = {"supports_pausing": True, "supports_downscaling": True}

VM_TABLE = "waldur_azure_virtualmachine"
RESOURCE_GROUP_TABLE = "waldur_azure_resourcegroup"
ARM_PREFIX = "/subscriptions/"
VM_PROVIDER_PATH = "/providers/Microsoft.Compute/virtualMachines/"

# (app_label, model, content type field, object id field) for generic pointers
# that may be empty: these rows outlive the Azure objects, so only the pointer
# goes.
NULLABLE_POINTERS = (
    ("marketplace", "Resource", "content_type", "object_id"),
    ("permissions", "UserRole", "content_type", "object_id"),
    ("quotas", "QuotaLimit", "content_type", "object_id"),
    ("quotas", "QuotaUsage", "content_type", "object_id"),
    ("billing", "PriceEstimate", "content_type", "object_id"),
    ("support", "Issue", "resource_content_type", "resource_object_id"),
    ("structure", "ServiceSettings", "content_type", "object_id"),
)

# Generic pointers that cannot be empty: the rows only describe the Azure
# objects.
REQUIRED_POINTERS = (
    ("logging", "Feed"),
    ("analytics", "DailyQuotaHistory"),
    ("permissions", "RoleAvailability"),
    ("user_actions", "UserAction"),
    ("reversion", "Version"),
)


def _revoke_roles(apps, model, object_ids):
    """Revoke active roles scoped to marketplace rows about to be deleted.

    Deleting an offering through the live model revokes its roles in a
    pre_delete handler; without that, the roles stay active with a scope that
    no longer resolves and cannot be revoked through the API. Resources get the
    same treatment for the same reason.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    UserRole = apps.get_model("permissions", "UserRole")
    content_type = ContentType.objects.filter(
        app_label="marketplace", model=model
    ).first()
    if content_type is None or not object_ids:
        return
    UserRole.objects.filter(
        content_type=content_type, object_id__in=object_ids, is_active=True
    ).update(
        is_active=False,
        expiration_time=timezone.now(),
        revoke_reason="Azure SQL Server offering removed",
    )


def _delete_sql_server_offerings(apps):
    """Delete Azure.SQLServer offerings the SQL Server removal did not reach.

    That removal ran as a waldur_azure migration, which never runs on a
    deployment that upgrades straight past it now that the app is gone.
    """
    Offering = apps.get_model("marketplace", "Offering")
    Resource = apps.get_model("marketplace", "Resource")

    offerings = Offering.objects.filter(type=SQL_SERVER_OFFERING_TYPE)
    offering_ids = list(offerings.values_list("id", flat=True))
    if not offering_ids:
        return
    resource_ids = list(
        Resource.objects.filter(offering_id__in=offering_ids).values_list(
            "id", flat=True
        )
    )
    _revoke_roles(apps, "offering", offering_ids)
    _revoke_roles(apps, "resource", resource_ids)

    # Cascades to plans, resources, orders and usages. Invoice items keep their
    # history: their resource foreign key is SET_NULL.
    offerings.delete()
    print(f"Deleted {len(offering_ids)} {SQL_SERVER_OFFERING_TYPE} offering(s).")


def _load_vms(connection, vm_ids):
    """Return {vm id: (name, backend_id, settings id, rg name, rg backend_id)}."""
    tables = connection.introspection.table_names()
    if not vm_ids or VM_TABLE not in tables or RESOURCE_GROUP_TABLE not in tables:
        return {}
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT vm.id, vm.name, vm.backend_id, vm.service_settings_id, "
            "rg.name, rg.backend_id "
            f"FROM {VM_TABLE} vm "  # noqa: S608 (table names are constants)
            f"LEFT JOIN {RESOURCE_GROUP_TABLE} rg ON rg.id = vm.resource_group_id "
            "WHERE vm.id = ANY(%s)",
            [list(vm_ids)],
        )
        return {row[0]: row[1:] for row in cursor.fetchall()}


def _arm_id(vm_name, vm_backend_id, rg_name, rg_backend_id, subscription_id):
    """Build the VM's full Azure resource ID, or None if it cannot be known.

    A created VM stores the ID itself. For an imported one it is assembled from
    the resource group's ID, or failing that from the subscription and the
    resource group's name.
    """
    if vm_backend_id and vm_backend_id.startswith(ARM_PREFIX):
        return vm_backend_id
    if not vm_name:
        return None
    if rg_backend_id and rg_backend_id.startswith(ARM_PREFIX):
        return f"{rg_backend_id}{VM_PROVIDER_PATH}{vm_name}"
    rg = rg_backend_id or rg_name
    if subscription_id and rg:
        return (
            f"{ARM_PREFIX}{subscription_id}/resourceGroups/{rg}"
            f"{VM_PROVIDER_PATH}{vm_name}"
        )
    return None


def _rewrite_backend_ids(apps, connection):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Resource = apps.get_model("marketplace", "Resource")
    ServiceSettings = apps.get_model("structure", "ServiceSettings")

    resources = list(
        Resource.objects.filter(offering__type=VM_OFFERING_TYPE).values_list(
            "id", "uuid", "name", "backend_id", "content_type_id", "object_id"
        )
    )
    if not resources:
        return

    vm_ct = ContentType.objects.filter(
        app_label="waldur_azure", model="virtualmachine"
    ).first()
    vm_ct_id = vm_ct.id if vm_ct else None
    vms = _load_vms(
        connection,
        [r[5] for r in resources if vm_ct_id and r[4] == vm_ct_id and r[5]],
    )

    settings_ids = {vm[2] for vm in vms.values() if vm[2]}
    subscriptions = {}
    for settings in ServiceSettings.objects.filter(id__in=settings_ids):
        options = settings.options if isinstance(settings.options, dict) else {}
        subscriptions[settings.id] = options.get("subscription_id")

    rewritten = skipped = 0
    for pk, uuid, name, backend_id, ct_id, object_id in resources:
        vm = vms.get(object_id) if vm_ct_id and ct_id == vm_ct_id else None
        arm_id = None
        if vm:
            vm_name, vm_backend_id, settings_id, rg_name, rg_backend_id = vm
            arm_id = _arm_id(
                vm_name,
                vm_backend_id,
                rg_name,
                rg_backend_id,
                subscriptions.get(settings_id),
            )
        if arm_id is None:
            if backend_id and backend_id.startswith(ARM_PREFIX):
                continue
            skipped += 1
            print(
                f"Skipping resource {uuid} ({name}): cannot resolve its Azure "
                f"resource ID; backend_id stays {backend_id!r}. Set it to the "
                "full resource ID before the site agent manages it."
            )
            continue
        if arm_id != backend_id:
            Resource.objects.filter(pk=pk).update(backend_id=arm_id)
            rewritten += 1

    print(
        f"Set the full Azure resource ID on {rewritten} resource(s); skipped {skipped}."
    )


def _convert_offerings(apps):
    Offering = apps.get_model("marketplace", "Offering")
    for offering in Offering.objects.filter(type=VM_OFFERING_TYPE):
        plugin_options = {**(offering.plugin_options or {}), **AGENT_PLUGIN_OPTIONS}
        # The scope pointed at the Azure service settings, which hold the
        # credentials mastermind no longer keeps; the agent has its own.
        Offering.objects.filter(pk=offering.pk).update(
            type=SITE_AGENT_OFFERING_TYPE,
            content_type=None,
            object_id=None,
            plugin_options=plugin_options,
        )
        print(
            f"Handing offering {offering.uuid} ({offering.name}) to the site "
            f"agent: its type is now {SITE_AGENT_OFFERING_TYPE}."
        )


def _clear_azure_pointers(apps):
    ContentType = apps.get_model("contenttypes", "ContentType")
    azure_cts = ContentType.objects.filter(app_label="waldur_azure")
    for app_label, model_name, ct_field, id_field in NULLABLE_POINTERS:
        model = apps.get_model(app_label, model_name)
        model.objects.filter(**{f"{ct_field}__in": azure_cts}).update(
            **{ct_field: None, id_field: None}
        )
    for app_label, model_name in REQUIRED_POINTERS:
        model = apps.get_model(app_label, model_name)
        model.objects.filter(content_type__in=azure_cts).delete()


def hand_azure_vms_to_site_agent(apps, schema_editor):
    _delete_sql_server_offerings(apps)
    # Resources are found by offering type and linked to their VM through the
    # generic pointer, so this runs before the offerings are converted and the
    # pointers cleared.
    _rewrite_backend_ids(apps, schema_editor.connection)
    _convert_offerings(apps)
    _clear_azure_pointers(apps)


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0286_service_provider_account"),
        ("invoices", "0031_credit_offerings_help_text"),
        ("structure", "0085_remove_project_display_credit_reports"),
        ("permissions", "0028_userrole_source"),
        ("quotas", "0005_drop_zero_usage"),
        ("billing", "0002_drop_limit_and_threshold"),
        ("support", "0001_squashed_0027"),
        ("logging", "0029_eventconsumer_auth_attribution"),
        ("analytics", "0001_squashed_0003"),
        ("user_actions", "0001_squashed_0007"),
        ("reversion", "0002_add_index_on_version_for_content_type_and_db"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        # Reverse is a noop: the previous offering types and backend ids are not
        # recorded, and the plugin that served them is gone.
        migrations.RunPython(hand_azure_vms_to_site_agent, migrations.RunPython.noop),
    ]
