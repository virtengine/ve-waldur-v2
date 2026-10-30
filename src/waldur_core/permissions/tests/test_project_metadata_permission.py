from importlib import import_module
from pathlib import Path

import yaml
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from rest_framework import test

from waldur_core.permissions.enums import PermissionEnum
from waldur_core.permissions.models import Role, RolePermission
from waldur_core.structure.models import Customer, Project

PERMISSIONS_YAML = Path(settings.BASE_DIR) / "docker/rootfs/etc/waldur/permissions.yaml"
PERMISSION = PermissionEnum.UPDATE_PROJECT_METADATA.value

migration = import_module(
    "waldur_core.permissions.migrations.0037_project_metadata_permission"
)


class ProjectMetadataPermissionGrantTest(test.APITestCase):
    def test_permissions_yaml_grants_it_to_owners_and_project_managers(self):
        holders = {
            row["role"]
            for row in yaml.safe_load(PERMISSIONS_YAML.read_text())
            if PERMISSION in row["permissions"]
        }
        self.assertEqual(holders, {"CUSTOMER.OWNER", "PROJECT.MANAGER"})


class ProjectMetadataPermissionMigrationTest(test.APITestCase):
    def system_role(self, name, model):
        role, _ = Role.objects.get_or_create(
            name=name,
            content_type=ContentType.objects.get_for_model(model),
            defaults={"is_system_role": True},
        )
        return role

    def test_owners_managers_and_their_clones_get_it(self):
        owner = self.system_role("CUSTOMER.OWNER", Customer)
        manager = self.system_role("PROJECT.MANAGER", Project)
        admin = self.system_role("PROJECT.ADMIN", Project)
        clones = [
            Role.objects.create(
                name="CUSTOMER.acme.OWNER",
                content_type=owner.content_type,
                template=owner,
            ),
            Role.objects.create(
                name="PROJECT.acme.MANAGER",
                content_type=manager.content_type,
                template=manager,
            ),
        ]
        unrelated = Role.objects.create(
            name="PROJECT.acme.OTHER", content_type=manager.content_type
        )
        RolePermission.objects.filter(permission=PERMISSION).delete()

        migration.grant_to_owners_and_managers(apps, None)
        migration.grant_to_owners_and_managers(apps, None)  # idempotent

        holders = RolePermission.objects.filter(permission=PERMISSION)
        self.assertEqual(
            sorted(holders.values_list("role__name", flat=True)),
            sorted([owner.name, manager.name, *[role.name for role in clones]]),
        )
        self.assertNotIn(admin.name, holders.values_list("role__name", flat=True))
        self.assertNotIn(unrelated.name, holders.values_list("role__name", flat=True))
