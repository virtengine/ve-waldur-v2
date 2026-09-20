"""Per-member sync status reporting, reading, and resync triggering.

The site agent reports how each role grant propagated to the provider
backend (set_membership_sync_statuses: a complete report that writes only
what changed), the team_members endpoint joins those rows onto roles[] /
resource_projects[] entries, and providers can trigger a resource-scoped
user role resync.
The whole feature is opt-in per offering via the
enable_membership_sync_status plugin option.
"""

import datetime

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from freezegun import freeze_time
from rest_framework import status, test
from rest_framework.reverse import reverse

from waldur_core.permissions.enums import PermissionEnum
from waldur_core.permissions.fixtures import OfferingRole
from waldur_core.permissions.models import Role
from waldur_core.structure.tests import fixtures
from waldur_core.structure.tests.factories import UserFactory
from waldur_mastermind.marketplace import models
from waldur_mastermind.marketplace.tests import factories


class _Base(test.APITestCase):
    def setUp(self) -> None:
        cache.clear()
        self.fixture = fixtures.ProjectFixture()
        self.offering = factories.OfferingFactory(
            customer=self.fixture.customer,
            plugin_options={
                "enable_resource_projects": True,
                "enable_membership_sync_status": True,
            },
        )
        self.resource = factories.ResourceFactory(
            project=self.fixture.project, offering=self.offering
        )
        self.member = UserFactory()
        resource_ct = ContentType.objects.get_for_model(models.Resource)
        self.custom_role = Role.objects.create(
            name="cluster_owner", content_type=resource_ct, is_system_role=False
        )
        self.resource.add_user(self.member, self.custom_role)

        self.offering_manager = UserFactory()
        # Test-DB system roles are created bare (migration 0002 imports no
        # permissions); grant exactly what production permissions.yaml
        # gives OFFERING.MANAGER for the paths under test.
        OfferingRole.MANAGER.add_permission(
            PermissionEnum.SET_RESOURCE_BACKEND_METADATA
        )
        OfferingRole.MANAGER.add_permission(PermissionEnum.UPDATE_OFFERING)
        self.offering.add_user(self.offering_manager, OfferingRole.MANAGER)

        self.report_url = factories.ResourceFactory.get_provider_resource_url(
            self.resource, action="set_membership_sync_statuses"
        )

    def _report(self, statuses):
        return self.client.post(self.report_url, {"statuses": statuses}, format="json")

    def _entry(self, **overrides):
        entry = {
            "username": self.member.username,
            "scope_type": "resource",
            "role_name": "cluster_owner",
            "state": "synced",
        }
        entry.update(overrides)
        return entry

    def _disable_flag(self):
        self.offering.plugin_options["enable_membership_sync_status"] = False
        self.offering.save(update_fields=["plugin_options"])


class ReportMembershipSyncStatusTest(_Base):
    def test_offering_manager_can_report(self):
        self.client.force_authenticate(self.offering_manager)
        response = self._report([self._entry()])
        self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)
        self.assertEqual(1, response.data["stored"])
        row = models.ResourceMemberSyncStatus.objects.get(resource=self.resource)
        self.assertEqual(self.member, row.user)
        self.assertEqual("synced", row.state)

    def test_report_replaces_previous_rows(self):
        self.client.force_authenticate(self.fixture.staff)
        self._report([self._entry(state="pending")])
        response = self._report(
            [self._entry(state="missing_in_idp", message="User not found in Keycloak")]
        )
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        rows = models.ResourceMemberSyncStatus.objects.filter(resource=self.resource)
        self.assertEqual(1, rows.count())
        self.assertEqual("missing_in_idp", rows.get().state)

    def test_unresolvable_user_is_skipped_not_fatal(self):
        self.client.force_authenticate(self.fixture.staff)
        response = self._report([self._entry(), self._entry(username="no-such-user")])
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, response.data["stored"])
        self.assertEqual(["no-such-user"], response.data["skipped"])

    def test_flag_off_returns_conflict(self):
        self._disable_flag()
        self.client.force_authenticate(self.fixture.staff)
        response = self._report([self._entry()])
        self.assertEqual(status.HTTP_409_CONFLICT, response.status_code)

    def test_project_manager_cannot_report(self):
        # Consumer-side users don't even see the resource through the
        # provider viewset (filter_for_service_provider) — 404, not 403.
        self.client.force_authenticate(self.fixture.manager)
        response = self._report([self._entry()])
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_resource_project_scope_row(self):
        rp = models.ResourceProject.objects.create(
            resource=self.resource, name="rp-1", state=models.ResourceProject.States.OK
        )
        rp_ct = ContentType.objects.get_for_model(models.ResourceProject)
        rp_role = Role.objects.create(
            name="ingress_manage", content_type=rp_ct, is_system_role=False
        )
        rp.add_user(self.member, rp_role)
        self.client.force_authenticate(self.fixture.staff)
        response = self._report(
            [
                self._entry(
                    scope_type="resource_project",
                    resource_project_uuid=rp.uuid.hex,
                    role_name="ingress_manage",
                )
            ]
        )
        self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)
        row = models.ResourceMemberSyncStatus.objects.get(resource=self.resource)
        self.assertEqual(rp, row.resource_project)


class TeamMembersSyncFieldsTest(_Base):
    def setUp(self) -> None:
        super().setUp()
        self.team_url = factories.ResourceFactory.get_url(
            self.resource, action="team_members"
        )

    def _member_row(self, response):
        return next(
            row for row in response.data if row["full_name"] == self.member.full_name
        )

    def test_sync_fields_present_and_joined_when_enabled(self):
        self.client.force_authenticate(self.fixture.staff)
        self._report(
            [self._entry(state="missing_in_idp", message="User not found in Keycloak")]
        )
        response = self.client.get(self.team_url, {"field": ["full_name", "roles"]})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        grant = self._member_row(response)["roles"][0]
        self.assertEqual("missing_in_idp", grant["sync_state"])
        self.assertEqual("User not found in Keycloak", grant["sync_message"])
        self.assertIsNotNone(grant["sync_reported_at"])

    def test_unreported_grant_serializes_null_state(self):
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.get(self.team_url, {"field": ["full_name", "roles"]})
        grant = self._member_row(response)["roles"][0]
        self.assertIn("sync_state", grant)
        self.assertIsNone(grant["sync_state"])

    def test_sync_fields_absent_when_flag_off(self):
        self._disable_flag()
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.get(self.team_url, {"field": ["full_name", "roles"]})
        grant = self._member_row(response)["roles"][0]
        self.assertNotIn("sync_state", grant)
        self.assertNotIn("sync_message", grant)
        self.assertNotIn("sync_reported_at", grant)


class ResourceSyncUserRolesTriggerTest(_Base):
    def setUp(self) -> None:
        super().setUp()
        self.trigger_url = "http://testserver" + reverse(
            "marketplace-provider-resource-sync-user-roles",
            kwargs={"uuid": self.resource.uuid.hex},
        )

    def test_staff_can_trigger(self):
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.post(self.trigger_url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_offering_manager_can_trigger(self):
        cache.clear()
        self.client.force_authenticate(self.offering_manager)
        response = self.client.post(self.trigger_url)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_repeat_trigger_is_throttled(self):
        self.client.force_authenticate(self.fixture.staff)
        first = self.client.post(self.trigger_url)
        second = self.client.post(self.trigger_url)
        self.assertEqual(status.HTTP_200_OK, first.status_code)
        self.assertEqual(status.HTTP_429_TOO_MANY_REQUESTS, second.status_code)

    def test_flag_off_returns_conflict(self):
        self._disable_flag()
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.post(self.trigger_url)
        self.assertEqual(status.HTTP_409_CONFLICT, response.status_code)

    def test_project_manager_cannot_trigger(self):
        self.client.force_authenticate(self.fixture.manager)
        response = self.client.post(self.trigger_url)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class PluginOptionRoundTripTest(test.APITestCase):
    """The flag must survive an offering integration update — i.e. it is
    declared on the plugin-options serializer, not silently dropped."""

    def test_flag_round_trips_through_update_integration(self):
        fixture = fixtures.ProjectFixture()
        offering = factories.OfferingFactory(customer=fixture.customer)
        self.client.force_authenticate(fixture.staff)
        url = factories.OfferingFactory.get_url(offering, action="update_integration")
        response = self.client.post(
            url,
            {"plugin_options": {"enable_membership_sync_status": True}},
            format="json",
        )
        self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)
        offering.refresh_from_db()
        self.assertTrue(offering.plugin_options.get("enable_membership_sync_status"))


class OfferingManagerStateTransitionTest(_Base):
    """A site agent authenticates with an offering-scoped OFFERING.MANAGER role.

    It must be able to drive the state of its own offering's resources and
    sub-projects (flip a reconciled sub-project to OK, mark a resource erred on
    a backend failure). Those endpoints historically accepted only the owning
    customer scope, so an offering-scoped caller got a 403 even though
    OFFERING.MANAGER already carries RESOURCE.SET_STATE / OFFERING.UPDATE.
    """

    def setUp(self) -> None:
        super().setUp()
        OfferingRole.MANAGER.add_permission(PermissionEnum.SET_RESOURCE_STATE)

    def test_offering_manager_can_set_resource_state_ok(self):
        self.resource.set_state_erred()
        self.resource.save(update_fields=["state"])
        self.client.force_authenticate(self.offering_manager)
        url = factories.ResourceFactory.get_provider_resource_url(
            self.resource, action="set_state_ok"
        )
        response = self.client.post(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)
        self.resource.refresh_from_db()
        self.assertEqual(models.Resource.States.OK, self.resource.state)

    def test_offering_manager_can_set_resource_as_erred(self):
        self.client.force_authenticate(self.offering_manager)
        url = factories.ResourceFactory.get_provider_resource_url(
            self.resource, action="set_as_erred"
        )
        response = self.client.post(url, {}, format="json")
        self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)
        self.resource.refresh_from_db()
        self.assertEqual(models.Resource.States.ERRED, self.resource.state)

    def test_offering_manager_can_set_sub_project_state_ok(self):
        rp = models.ResourceProject.objects.create(
            resource=self.resource,
            name="rp-1",
            state=models.ResourceProject.States.CREATING,
        )
        self.client.force_authenticate(self.offering_manager)
        url = reverse(
            "marketplace-provider-resource-project-set-state-ok",
            kwargs={"uuid": rp.uuid.hex},
        )
        response = self.client.post(url)
        self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)
        rp.refresh_from_db()
        self.assertEqual(models.ResourceProject.States.OK, rp.state)

    def test_project_manager_cannot_set_resource_state(self):
        # A consumer-side project manager must not gain provider state powers.
        self.resource.set_state_erred()
        self.resource.save(update_fields=["state"])
        self.client.force_authenticate(self.fixture.manager)
        url = factories.ResourceFactory.get_provider_resource_url(
            self.resource, action="set_state_ok"
        )
        response = self.client.post(url)
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )


class TeamMembersQueryCountTest(_Base):
    """team_members must not issue a query per member.

    The per-member serializer fields (roles, resource_projects, scalar
    role_name/role_uuid/expiration_time) previously each queried UserRole
    per row. The view now bulk-loads grants into context, so the query
    count is bounded regardless of team size.
    """

    def setUp(self) -> None:
        super().setUp()
        self.team_url = factories.ResourceFactory.get_url(
            self.resource, action="team_members"
        )
        self.rp = models.ResourceProject.objects.create(
            resource=self.resource,
            name="rp-1",
            state=models.ResourceProject.States.OK,
        )
        self.rp_role = Role.objects.create(
            name="ingress_manage",
            content_type=ContentType.objects.get_for_model(models.ResourceProject),
            is_system_role=False,
        )

    def _add_members(self, count):
        for _ in range(count):
            user = UserFactory()
            self.resource.add_user(user, self.custom_role)
            self.rp.add_user(user, self.rp_role)

    def _fetch(self):
        response = self.client.get(self.team_url, {"page_size": 100})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        data = response.data
        # team_members returns a bare list; tolerate a paginated envelope too.
        results = data["results"] if isinstance(data, dict) else data
        return list(results)

    def test_query_count_does_not_grow_with_team_size(self):
        self.client.force_authenticate(self.fixture.staff)
        self._add_members(3)
        # Warm up content-type/permission caches so the first measured call
        # isn't charged for one-time lookups.
        self._fetch()
        with CaptureQueriesContext(connection) as small_ctx:
            small_members = len(self._fetch())

        self._add_members(12)
        with CaptureQueriesContext(connection) as large_ctx:
            large_members = len(self._fetch())

        # Guard: the large call really did serialize more members.
        self.assertGreater(large_members, small_members)
        self.assertGreaterEqual(large_members, 15)

        self.assertEqual(
            len(small_ctx.captured_queries),
            len(large_ctx.captured_queries),
            "team_members query count scales with team size "
            f"({len(small_ctx.captured_queries)} for {small_members} members "
            f"vs {len(large_ctx.captured_queries)} for {large_members}) — "
            "per-member N+1 regression",
        )


T1 = datetime.datetime(2026, 1, 1, 10, 0, tzinfo=datetime.UTC)
T2 = datetime.datetime(2026, 1, 1, 11, 0, tzinfo=datetime.UTC)
STATUS_TABLE = models.ResourceMemberSyncStatus._meta.db_table


class ReportDiffTest(_Base):
    """A report writes only what changed; the report time is kept per resource.

    The agent reports on every sync cycle and most reports change nothing,
    so an unchanged report must not rewrite the resource's rows.
    """

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.fixture.staff)
        self.other = UserFactory()
        self.resource.add_user(self.other, self.custom_role)
        self.team_url = factories.ResourceFactory.get_url(
            self.resource, action="team_members"
        )

    def _rows(self):
        return {
            row.user_id: row
            for row in models.ResourceMemberSyncStatus.objects.filter(
                resource=self.resource
            )
        }

    def _reported_at(self):
        return models.ResourceMemberSyncReport.objects.get(
            resource=self.resource
        ).reported_at

    def _entries(self):
        return [
            self._entry(),
            self._entry(username=self.other.username, state="error", message="boom"),
        ]

    def test_unchanged_report_writes_no_rows_and_records_the_report(self):
        with freeze_time(T1):
            self._report(self._entries())
        before = {uid: (row.id, row.modified) for uid, row in self._rows().items()}

        with freeze_time(T2), CaptureQueriesContext(connection) as ctx:
            response = self._report(self._entries())

        self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)
        self.assertEqual(2, response.data["stored"])
        after = {uid: (row.id, row.modified) for uid, row in self._rows().items()}
        self.assertEqual(before, after)
        self.assertEqual(T2, self._reported_at())
        row_writes = [
            query["sql"]
            for query in ctx.captured_queries
            if STATUS_TABLE in query["sql"]
            and query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        ]
        self.assertEqual([], row_writes)

    def test_changed_state_updates_the_row_in_place(self):
        with freeze_time(T1):
            self._report([self._entry(state="pending")])
        row_id = self._rows()[self.member.id].id

        with freeze_time(T2):
            self._report([self._entry(state="synced")])

        row = self._rows()[self.member.id]
        self.assertEqual(row_id, row.id)
        self.assertEqual("synced", row.state)
        self.assertEqual(T2, row.modified)

    def test_changed_message_alone_updates_the_row(self):
        self._report([self._entry(state="error", message="first")])
        self._report([self._entry(state="error", message="second")])
        self.assertEqual("second", self._rows()[self.member.id].message)

    def test_dropped_grant_is_deleted_and_new_grant_created(self):
        self._report([self._entry()])
        self._report([self._entry(username=self.other.username)])
        self.assertEqual({self.other.id}, set(self._rows()))

    def test_grant_listed_twice_is_stored_once(self):
        response = self._report(
            [self._entry(state="pending"), self._entry(state="synced")]
        )
        self.assertEqual(1, response.data["stored"])
        rows = models.ResourceMemberSyncStatus.objects.filter(resource=self.resource)
        self.assertEqual(1, rows.count())
        self.assertEqual("synced", rows.get().state)

    def test_duplicate_rows_left_by_earlier_reports_are_collapsed(self):
        for _ in range(2):
            models.ResourceMemberSyncStatus.objects.create(
                resource=self.resource,
                user=self.member,
                scope_type="resource",
                role_name="cluster_owner",
                state="pending",
            )
        self._report([self._entry(state="synced")])
        rows = models.ResourceMemberSyncStatus.objects.filter(resource=self.resource)
        self.assertEqual(1, rows.count())
        self.assertEqual("synced", rows.get().state)

    def test_empty_report_clears_rows_and_records_the_report(self):
        self._report([self._entry()])
        with freeze_time(T2):
            response = self._report([])
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({}, self._rows())
        self.assertEqual(T2, self._reported_at())

    def _grant(self):
        response = self.client.get(self.team_url, {"field": ["full_name", "roles"]})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        member = next(
            row for row in response.data if row["full_name"] == self.member.full_name
        )
        return member["roles"][0]

    def test_team_members_shows_the_last_report_time(self):
        with freeze_time(T1):
            self._report([self._entry()])
        with freeze_time(T2):
            self._report([self._entry()])
        self.assertEqual(T2, self._grant()["sync_reported_at"])

    def test_rows_without_a_report_record_fall_back_to_their_own_time(self):
        with freeze_time(T1):
            models.ResourceMemberSyncStatus.objects.create(
                resource=self.resource,
                user=self.member,
                scope_type="resource",
                role_name="cluster_owner",
                state="synced",
            )
        self.assertEqual(T1, self._grant()["sync_reported_at"])


class ReportValidationTest(_Base):
    """Malformed entries from an agent are rejected with 400, never a 500."""

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.fixture.staff)

    def test_role_name_longer_than_the_column_is_rejected(self):
        response = self._report([self._entry(role_name="r" * 151)])

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertFalse(
            models.ResourceMemberSyncStatus.objects.filter(
                resource=self.resource
            ).exists()
        )

    def test_role_name_at_the_column_limit_is_accepted(self):
        response = self._report([self._entry(role_name="r" * 150)])

        self.assertEqual(status.HTTP_200_OK, response.status_code, response.data)
