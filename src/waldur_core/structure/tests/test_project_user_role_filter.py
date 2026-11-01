from rest_framework import status, test

from waldur_core.permissions.enums import RoleEnum
from waldur_core.permissions.fixtures import ProjectRole
from waldur_core.permissions.models import Role
from waldur_core.permissions.serializers import clone_role_for_customer
from waldur_core.structure.tests import factories, fixtures

PROJECT_ADMIN = RoleEnum.PROJECT_ADMIN


class ProjectUserRoleFilterTest(test.APITestCase):
    def setUp(self):
        self.fixture = fixtures.ProjectFixture()
        self.project = self.fixture.project
        self.admin = self.fixture.admin
        self.manager = self.fixture.manager
        factories.ProjectFactory(customer=self.fixture.customer)
        self.client.force_authenticate(self.fixture.staff)

    def list_projects(self, user, role=PROJECT_ADMIN):
        return self.client.get(
            factories.ProjectFactory.get_list_url(),
            {"user_uuid_with_active_role": user.uuid.hex, "user_role": role},
        ).data

    def test_filter_by_role_name(self):
        self.assertEqual(
            [row["uuid"] for row in self.list_projects(self.admin)],
            [self.project.uuid.hex],
        )

    def test_filter_by_role_uuid(self):
        role = Role.objects.get(name=PROJECT_ADMIN)
        self.assertEqual(
            [row["uuid"] for row in self.list_projects(self.admin, role.uuid.hex)],
            [self.project.uuid.hex],
        )

    def test_filter_ignores_other_roles(self):
        self.assertEqual(self.list_projects(self.manager), [])

    def test_filter_ignores_revoked_administrator(self):
        self.project.remove_user(self.admin)
        self.assertEqual(self.list_projects(self.admin), [])


class ProjectUserRoleFilterOrganizationCopyTest(test.APITestCase):
    def setUp(self):
        self.fixture = fixtures.ProjectFixture()
        self.project = self.fixture.project
        self.admin = self.fixture.admin
        self.copy = clone_role_for_customer(ProjectRole.ADMIN, self.fixture.customer)
        self.copy_holder = factories.UserFactory()
        self.copy_project = factories.ProjectFactory(customer=self.fixture.customer)
        self.copy_project.add_user(self.copy_holder, self.copy)
        self.client.force_authenticate(self.fixture.staff)

    def project_uuids(self, user, role):
        response = self.client.get(
            factories.ProjectFactory.get_list_url(),
            {"user_uuid_with_active_role": user.uuid.hex, "user_role": role},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return [row["uuid"] for row in response.data]

    def test_role_name_includes_organization_copy(self):
        self.assertEqual(
            self.project_uuids(self.copy_holder, PROJECT_ADMIN),
            [self.copy_project.uuid.hex],
        )

    def test_role_uuid_includes_organization_copy(self):
        role = Role.objects.get(name=PROJECT_ADMIN)
        self.assertEqual(
            self.project_uuids(self.copy_holder, role.uuid.hex),
            [self.copy_project.uuid.hex],
        )

    def test_copy_name_matches_only_that_copy(self):
        self.assertEqual(
            self.project_uuids(self.copy_holder, self.copy.name),
            [self.copy_project.uuid.hex],
        )
        self.assertEqual(self.project_uuids(self.admin, self.copy.name), [])

    def test_copy_uuid_matches_only_that_copy(self):
        self.assertEqual(
            self.project_uuids(self.copy_holder, self.copy.uuid.hex),
            [self.copy_project.uuid.hex],
        )
        self.assertEqual(self.project_uuids(self.admin, self.copy.uuid.hex), [])

    def test_copy_of_another_role_is_not_included(self):
        manager_copy = clone_role_for_customer(
            ProjectRole.MANAGER, self.fixture.customer
        )
        manager = factories.UserFactory()
        self.project.add_user(manager, manager_copy)
        self.assertEqual(self.project_uuids(manager, PROJECT_ADMIN), [])

    def test_revoked_copy_holder_is_not_included(self):
        self.copy_project.remove_user(self.copy_holder)
        self.assertEqual(self.project_uuids(self.copy_holder, PROJECT_ADMIN), [])
