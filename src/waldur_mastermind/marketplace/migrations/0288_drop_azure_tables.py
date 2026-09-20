from django.db import migrations

# Removing the waldur_azure app leaves its tables behind: Django only removes
# tables it is told to remove, and an app it no longer knows about cannot be
# told.
#
# Leaving them is not merely untidy. The Azure models subclassed structure base
# models, so their tables still carry real FK constraints to structure_project
# and structure_servicesettings. Django performs cascades in Python, not via ON
# DELETE CASCADE, so once the app is gone the ORM no longer knows these rows
# exist -- and deleting a Project or ServiceSettings that still has one fails at
# the database with an IntegrityError the ORM cannot explain.
#
# The Azure service settings go too. They hold the service principal
# credentials (subscription_id, tenant_id, client_id, client_secret), and
# mastermind no longer makes any Azure call that would need them: the site
# agent holds its own copy. Keeping them would only keep a cloud credential in a
# database that has no use for it. Operators copy them into the agent's
# configuration before upgrading.
#
# 0287 read what it needed from these tables and cleared the generic pointers at
# their rows, so both can go now. Irreversible: reversing restores the migration
# record, not the data.

AZURE_SERVICE_TYPE = "Azure"

DROP_TABLES = """
DROP TABLE IF EXISTS waldur_azure_sqldatabase CASCADE;
DROP TABLE IF EXISTS waldur_azure_sqlserver CASCADE;
DROP TABLE IF EXISTS waldur_azure_virtualmachine CASCADE;
DROP TABLE IF EXISTS waldur_azure_publicip CASCADE;
DROP TABLE IF EXISTS waldur_azure_networkinterface CASCADE;
DROP TABLE IF EXISTS waldur_azure_securitygroup CASCADE;
DROP TABLE IF EXISTS waldur_azure_subnet CASCADE;
DROP TABLE IF EXISTS waldur_azure_network CASCADE;
DROP TABLE IF EXISTS waldur_azure_storageaccount CASCADE;
DROP TABLE IF EXISTS waldur_azure_resourcegroup CASCADE;
DROP TABLE IF EXISTS waldur_azure_sizeavailabilityzone CASCADE;
DROP TABLE IF EXISTS waldur_azure_size CASCADE;
DROP TABLE IF EXISTS waldur_azure_image CASCADE;
DROP TABLE IF EXISTS waldur_azure_location CASCADE;
"""

# (app_label, model, content type field, object id field) for generic pointers
# that may be empty: these rows outlive the service settings, so only the
# pointer goes.
NULLABLE_POINTERS = (
    ("marketplace", "Offering", "content_type", "object_id"),
    ("marketplace", "Resource", "content_type", "object_id"),
    ("permissions", "UserRole", "content_type", "object_id"),
    ("quotas", "QuotaLimit", "content_type", "object_id"),
    ("quotas", "QuotaUsage", "content_type", "object_id"),
    ("billing", "PriceEstimate", "content_type", "object_id"),
    ("support", "Issue", "resource_content_type", "resource_object_id"),
    ("structure", "ServiceSettings", "content_type", "object_id"),
)

# Generic pointers that cannot be empty: the rows only describe the settings.
REQUIRED_POINTERS = (
    ("logging", "Feed"),
    ("analytics", "DailyQuotaHistory"),
    ("permissions", "RoleAvailability"),
    ("user_actions", "UserAction"),
    ("reversion", "Version"),
)


def delete_azure_service_settings(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ServiceSettings = apps.get_model("structure", "ServiceSettings")

    settings_ids = list(
        ServiceSettings.objects.filter(type=AZURE_SERVICE_TYPE).values_list(
            "id", flat=True
        )
    )
    if not settings_ids:
        return

    # Deleting through a historical model runs no handlers and the database
    # does not enforce GenericForeignKey cascades, so pointers at these rows
    # are cleared by hand first.
    settings_ct = ContentType.objects.filter(
        app_label="structure", model="servicesettings"
    ).first()
    if settings_ct is not None:
        for app_label, model_name, ct_field, id_field in NULLABLE_POINTERS:
            model = apps.get_model(app_label, model_name)
            model.objects.filter(
                **{ct_field: settings_ct, f"{id_field}__in": settings_ids}
            ).update(**{ct_field: None, id_field: None})
        for app_label, model_name in REQUIRED_POINTERS:
            model = apps.get_model(app_label, model_name)
            # reversion.Version keeps object_id as text.
            object_ids = (
                [str(pk) for pk in settings_ids]
                if model_name == "Version"
                else settings_ids
            )
            model.objects.filter(
                content_type=settings_ct, object_id__in=object_ids
            ).delete()

    ServiceSettings.objects.filter(id__in=settings_ids).delete()
    print(
        f"Deleted {len(settings_ids)} {AZURE_SERVICE_TYPE} service setting(s): "
        "their credentials belong in the site agent's configuration."
    )


def drop_azure_content_types(apps, schema_editor):
    """Remove the now-dangling content types for the deleted app.

    0287 needed these rows to find the pointers it cleared, so they could not
    be removed until after it ran. This cascades to the matching
    auth.Permission rows, which is what `remove_stale_contenttypes` would do
    anyway.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="waldur_azure").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0287_hand_azure_vms_to_site_agent"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        # Irreversible: reversing restores the migration record but not the data.
        migrations.RunSQL(DROP_TABLES, migrations.RunSQL.noop),
        migrations.RunPython(delete_azure_service_settings, migrations.RunPython.noop),
        migrations.RunPython(drop_azure_content_types, migrations.RunPython.noop),
    ]
