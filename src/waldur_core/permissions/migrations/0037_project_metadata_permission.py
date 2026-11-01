from django.db import migrations

# Mirrors docker/rootfs/etc/waldur/permissions.yaml. import_roles fixes the
# system roles on the next deploy, but clones (CUSTOMER.<slug>.OWNER,
# PROJECT.<slug>.MANAGER) copied their template's permissions once and never see
# later additions, and stacks that skip initdb never run import_roles at all.
# Without it, owners and managers on a clone would get no edit button on a
# project's metadata checklist, which HomePort shows to holders of this.
PERMISSION = "PROJECT.UPDATE_METADATA"
TEMPLATES = {"customer": "CUSTOMER.OWNER", "project": "PROJECT.MANAGER"}


def grant_to_owners_and_managers(apps, schema_editor):
    Role = apps.get_model("permissions", "Role")
    RolePermission = apps.get_model("permissions", "RolePermission")
    for scope, template in TEMPLATES.items():
        roles = Role.objects.filter(
            content_type__model=scope, is_system_role=True, name=template
        )
        clones = Role.objects.filter(
            content_type__model=scope,
            template__name=template,
            template__is_system_role=True,
        )
        for role in roles.union(clones):
            RolePermission.objects.get_or_create(role=role, permission=PERMISSION)


class Migration(migrations.Migration):
    dependencies = [
        ("permissions", "0036_global_role_scope"),
    ]

    operations = [
        migrations.RunPython(grant_to_owners_and_managers, migrations.RunPython.noop)
    ]
