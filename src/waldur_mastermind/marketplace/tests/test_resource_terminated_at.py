from datetime import timedelta

from django.apps import apps as live_apps
from django.utils import timezone
from freezegun import freeze_time
from rest_framework import status, test

from waldur_core.structure.tests import fixtures
from waldur_mastermind.marketplace import enums, models
from waldur_mastermind.marketplace.migrations._backfill_resource_terminated_at import (
    backfill_resource_terminated_at,
)
from waldur_mastermind.marketplace.tests import factories

States = models.Resource.States


class ResourceTerminatedAtTest(test.APITestCase):
    def setUp(self):
        self.resource = factories.ResourceFactory(state=States.OK)

    def terminate(self):
        self.resource.set_state_terminated()
        self.resource.save()

    def reload(self):
        return models.Resource.objects.get(pk=self.resource.pk)

    @freeze_time("2026-03-01 12:00:00")
    def test_transition_records_the_moment(self):
        self.terminate()

        self.assertEqual(self.reload().terminated_at, timezone.now())

    @freeze_time("2026-03-01 12:00:00")
    def test_direct_assignment_saving_only_state_records_it(self):
        # marketplace_remote assigns the state instead of using the transition.
        self.resource.state = States.TERMINATED
        self.resource.save(update_fields=["state"])

        self.assertEqual(self.reload().terminated_at, timezone.now())

    def test_update_fields_may_be_any_iterable(self):
        self.resource.state = States.TERMINATED
        self.resource.save(update_fields=("state",))

        self.assertIsNotNone(self.reload().terminated_at)

    def test_later_saves_do_not_move_it(self):
        with freeze_time("2026-03-01 12:00:00"):
            self.terminate()
            terminated_at = timezone.now()

        with freeze_time("2026-04-01 12:00:00"):
            resource = self.reload()
            resource.name = "renamed"
            resource.save()

        self.assertEqual(self.reload().terminated_at, terminated_at)

    def test_state_not_being_written_records_nothing(self):
        self.resource.state = States.TERMINATED
        self.resource.save(update_fields=["name"])

        self.assertIsNone(self.reload().terminated_at)

    def test_other_states_record_nothing(self):
        self.resource.set_state_updating()
        self.resource.save()

        self.assertIsNone(self.reload().terminated_at)

    def test_created_as_terminated_is_not_stamped(self):
        # An import creates the row in its final state: "now" would be the
        # moment of the import, not of the termination.
        resource = factories.ResourceFactory(state=States.TERMINATED)

        resource.refresh_from_db()
        self.assertIsNone(resource.terminated_at)

    def test_refused_restore_keeps_the_original_date(self):
        with freeze_time("2026-03-01 12:00:00"):
            self.terminate()
            terminated_at = timezone.now()

        with freeze_time("2026-04-01 12:00:00"):
            resource = self.reload()
            resource.set_state_creating()
            resource.save()
            self.assertEqual(self.reload().terminated_at, terminated_at)

            resource.set_state_terminated()
            resource.save()

        self.assertEqual(self.reload().terminated_at, terminated_at)

    def test_refused_restore_of_an_undated_resource_invents_no_date(self):
        # Long dead, with nothing to date it by: the refusal is not its end.
        resource = factories.ResourceFactory(state=States.TERMINATED)
        resource.set_state_creating()
        resource.save(update_fields=["state"])
        self.add_order(resource, enums.OrderTypes.RESTORE, enums.OrderStates.REJECTED)

        resource.set_state_terminated()
        resource.save(update_fields=["state"])

        resource.refresh_from_db()
        self.assertIsNone(resource.terminated_at)

    @freeze_time("2026-03-01 12:00:00")
    def test_refused_creation_records_the_moment(self):
        resource = factories.ResourceFactory(state=States.CREATING)
        factories.OrderFactory(
            resource=resource,
            project=resource.project,
            offering=resource.offering,
            type=enums.OrderTypes.CREATE,
        )

        resource.set_state_terminated()
        resource.save(update_fields=["state"])

        resource.refresh_from_db()
        self.assertEqual(resource.terminated_at, timezone.now())

    def test_failed_restore_keeps_the_original_date(self):
        with freeze_time("2026-03-01 12:00:00"):
            self.terminate()
            terminated_at = timezone.now()

        with freeze_time("2026-04-01 12:00:00"):
            resource = self.reload()
            resource.set_state_creating()
            resource.save()
            resource.set_state_erred()
            resource.save(update_fields=["state"])
            self.assertEqual(self.reload().terminated_at, terminated_at)

            resource.set_state_terminated()
            resource.save()

        self.assertEqual(self.reload().terminated_at, terminated_at)

    def add_order(self, resource, type, state=enums.OrderStates.ERRED):
        return factories.OrderFactory(
            resource=resource,
            project=resource.project,
            offering=resource.offering,
            type=type,
            state=state,
        )

    def fail_restore(self, resource):
        resource.set_state_creating()
        resource.save(update_fields=["state"])
        self.add_order(resource, enums.OrderTypes.RESTORE)
        resource.set_state_erred()
        resource.save(update_fields=["state"])

    def test_failed_restore_of_an_undated_resource_invents_no_date(self):
        resource = factories.ResourceFactory(state=States.TERMINATED)
        self.fail_restore(resource)

        resource.set_state_terminated()
        resource.save(update_fields=["state"])

        resource.refresh_from_db()
        self.assertIsNone(resource.terminated_at)

    def test_terminate_order_after_failed_restore_records_its_own_moment(self):
        # Left erred, the resource may hold a half-built backend, and removing
        # that is a termination. It does not pass through TERMINATING: the
        # handler leaves an erred resource alone.
        with freeze_time("2026-03-01 12:00:00"):
            self.terminate()

        resource = self.reload()
        self.fail_restore(resource)
        self.add_order(resource, enums.OrderTypes.TERMINATE, enums.OrderStates.DONE)

        with freeze_time("2026-05-01 12:00:00"):
            resource.set_state_terminated()
            resource.save(update_fields=["state"])
            self.assertEqual(self.reload().terminated_at, timezone.now())

    def test_terminate_order_that_did_not_run_keeps_the_date(self):
        with freeze_time("2026-03-01 12:00:00"):
            self.terminate()
            terminated_at = timezone.now()

        resource = self.reload()
        self.fail_restore(resource)
        self.add_order(resource, enums.OrderTypes.TERMINATE, enums.OrderStates.ERRED)

        with freeze_time("2026-05-01 12:00:00"):
            resource.set_state_terminated()
            resource.save(update_fields=["state"])

        self.assertEqual(self.reload().terminated_at, terminated_at)

    def test_terminate_order_still_executing_records_its_own_moment(self):
        # processors save the resource before completing the order.
        with freeze_time("2026-03-01 12:00:00"):
            self.terminate()

        resource = self.reload()
        self.fail_restore(resource)
        self.add_order(
            resource, enums.OrderTypes.TERMINATE, enums.OrderStates.EXECUTING
        )

        with freeze_time("2026-05-01 12:00:00"):
            resource.set_state_terminated()
            resource.save(update_fields=["state"])
            self.assertEqual(self.reload().terminated_at, timezone.now())

    def test_retrying_a_stale_terminate_order_keeps_the_date(self):
        # Retry only checks the order, and TERMINATING accepts any source.
        with freeze_time("2026-02-01 12:00:00"):
            stale_order = self.add_order(self.resource, enums.OrderTypes.TERMINATE)

        with freeze_time("2026-03-01 12:00:00"):
            self.add_order(
                self.resource, enums.OrderTypes.TERMINATE, enums.OrderStates.DONE
            )
            self.terminate()
            terminated_at = timezone.now()

        with freeze_time("2026-05-01 12:00:00"):
            resource = self.reload()
            resource.set_state_terminating()
            resource.save(update_fields=["state"])
            stale_order.set_state_executing()
            stale_order.save(update_fields=["state"])

            resource.set_state_terminated()
            resource.save(update_fields=["state"])

        self.assertEqual(self.reload().terminated_at, terminated_at)

    @freeze_time("2026-05-01 12:00:00")
    def test_terminating_records_its_own_moment_over_a_kept_date(self):
        resource = factories.ResourceFactory(
            state=States.ERRED,
            terminated_at=timezone.now() - timedelta(days=30),
        )

        self.add_order(
            resource, enums.OrderTypes.TERMINATE, enums.OrderStates.EXECUTING
        )
        resource.set_state_terminating()
        resource.save(update_fields=["state"])
        resource.set_state_terminated()
        resource.save(update_fields=["state"])

        resource.refresh_from_db()
        self.assertEqual(resource.terminated_at, timezone.now())

    @freeze_time("2026-05-01 12:00:00")
    def test_old_completed_restore_does_not_hide_a_later_end(self):
        resource = factories.ResourceFactory(state=States.ERRED)
        self.add_order(resource, enums.OrderTypes.RESTORE, enums.OrderStates.DONE)
        resource.set_state_creating()
        resource.save(update_fields=["state"])

        resource.set_state_terminated()
        resource.save(update_fields=["state"])

        resource.refresh_from_db()
        self.assertEqual(resource.terminated_at, timezone.now())

    @freeze_time("2026-05-01 12:00:00")
    def test_old_failed_restore_does_not_hide_the_end_of_a_revived_resource(self):
        # A remote sync can bring a resource back without completing the order.
        resource = factories.ResourceFactory(state=States.TERMINATED)
        self.fail_restore(resource)
        resource.state = States.OK
        resource.save(update_fields=["state"])

        resource.state = States.TERMINATED
        resource.save(update_fields=["state"])

        resource.refresh_from_db()
        self.assertEqual(resource.terminated_at, timezone.now())

    def test_erring_and_returning_to_terminated_keeps_the_date(self):
        # set_as_erred has no state check, and the transition's source is "*".
        with freeze_time("2026-03-01 12:00:00"):
            self.add_order(
                self.resource, enums.OrderTypes.TERMINATE, enums.OrderStates.DONE
            )
            self.terminate()
            terminated_at = timezone.now()

        with freeze_time("2026-05-01 12:00:00"):
            resource = self.reload()
            resource.set_state_erred()
            resource.save(update_fields=["state"])
            self.assertEqual(self.reload().terminated_at, terminated_at)

            resource.set_state_terminated()
            resource.save(update_fields=["state"])

        self.assertEqual(self.reload().terminated_at, terminated_at)

    def test_successful_restore_clears_it_and_termination_records_again(self):
        with freeze_time("2026-03-01 12:00:00"):
            self.terminate()

        resource = self.reload()
        resource.set_state_creating()
        resource.save()
        resource.set_state_ok()
        resource.save()
        self.assertIsNone(self.reload().terminated_at)

        with freeze_time("2026-05-01 12:00:00"):
            resource.set_state_terminated()
            resource.save()
            self.assertEqual(self.reload().terminated_at, timezone.now())

    def test_clearing_is_persisted_when_saving_only_state(self):
        self.terminate()

        # marketplace_remote can pull a resource straight out of TERMINATED.
        resource = self.reload()
        resource.state = States.OK
        resource.save(update_fields=["state"])

        self.assertIsNone(self.reload().terminated_at)


class ResourceTerminatedAtApiTest(test.APITestCase):
    def setUp(self):
        self.fixture = fixtures.ProjectFixture()
        self.resource = factories.ResourceFactory(
            project=self.fixture.project, state=States.OK
        )
        self.url = factories.ResourceFactory.get_url(self.resource)

    def test_api_returns_it(self):
        self.resource.set_state_terminated()
        self.resource.save()
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["terminated_at"])

    def test_api_returns_null_for_a_live_resource(self):
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.get(self.url)

        self.assertIsNone(response.data["terminated_at"])

    def test_api_cannot_set_it(self):
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.patch(
            self.url, {"terminated_at": "2020-01-01T00:00:00Z"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resource.refresh_from_db()
        self.assertIsNone(self.resource.terminated_at)


class BackfillTerminatedAtTest(test.APITestCase):
    """The migration function runs directly against the live app registry
    (django_test_migrations is not available)."""

    def setUp(self):
        self.now = timezone.now().replace(microsecond=0)
        self.resource = factories.ResourceFactory(state=States.TERMINATED)
        self.period_start = self.now - timedelta(days=100)

    def add_order(self, completed_at, type=enums.OrderTypes.TERMINATE, **kwargs):
        kwargs.setdefault("state", enums.OrderStates.DONE)
        order = factories.OrderFactory(
            resource=self.resource,
            project=self.resource.project,
            offering=self.resource.offering,
            type=type,
            **kwargs,
        )
        # Transitions and factories set it on their own: pin it.
        models.Order.objects.filter(pk=order.pk).update(completed_at=completed_at)

    def add_period(self, start, end):
        return models.ResourcePlanPeriod.objects.create(
            resource=self.resource,
            plan=self.resource.plan,
            start=start,
            end=end,
        )

    def backfilled(self):
        backfill_resource_terminated_at(live_apps, None)
        self.resource.refresh_from_db()
        return self.resource.terminated_at

    def test_uses_the_latest_terminate_order(self):
        first = self.now - timedelta(days=30)
        latest = self.now - timedelta(days=10)
        self.add_order(first)
        self.add_order(latest)

        self.assertEqual(self.backfilled(), latest)

    def test_uses_the_later_of_order_and_plan_period(self):
        # Revived with no restore order, terminated later with no terminate one.
        end = self.now - timedelta(days=10)
        self.add_order(self.now - timedelta(days=60))
        self.add_period(self.period_start, end)

        self.assertEqual(self.backfilled(), end)

    def test_order_is_used_when_it_is_the_later(self):
        completed_at = self.now - timedelta(days=10)
        self.add_order(completed_at)
        self.add_period(self.period_start, self.now - timedelta(days=11))

        self.assertEqual(self.backfilled(), completed_at)

    def test_ignores_terminate_order_undone_by_a_restore(self):
        self.add_order(self.now - timedelta(days=60))
        self.add_order(self.now - timedelta(days=30), type=enums.OrderTypes.RESTORE)

        self.assertIsNone(self.backfilled())

    def test_terminate_order_after_a_restore_counts(self):
        completed_at = self.now - timedelta(days=10)
        self.add_order(self.now - timedelta(days=60))
        self.add_order(self.now - timedelta(days=30), type=enums.OrderTypes.RESTORE)
        self.add_order(completed_at)

        self.assertEqual(self.backfilled(), completed_at)

    def test_ignores_orders_that_did_not_terminate(self):
        ignored = self.now - timedelta(days=10)
        self.add_order(ignored, type=enums.OrderTypes.UPDATE)
        self.add_order(ignored, state=enums.OrderStates.ERRED)

        self.assertIsNone(self.backfilled())

    def test_falls_back_when_the_order_has_no_completion_time(self):
        end = self.now - timedelta(days=9)
        self.add_order(None)
        self.add_period(self.period_start, end)

        self.assertEqual(self.backfilled(), end)

    def test_falls_back_to_the_end_of_the_latest_plan_period(self):
        self.add_period(self.period_start, self.now - timedelta(days=50))
        end = self.now - timedelta(days=9)
        self.add_period(self.now - timedelta(days=50), end)

        self.assertEqual(self.backfilled(), end)

    def test_open_plan_period_gives_no_date(self):
        # The closed one ended at a plan switch, not at the termination.
        self.add_period(self.period_start, self.now - timedelta(days=50))
        self.add_period(self.now - timedelta(days=50), None)

        self.assertIsNone(self.backfilled())

    def test_no_evidence_stays_empty(self):
        self.assertIsNone(self.backfilled())

    def test_leaves_other_states_alone(self):
        self.resource.state = States.OK
        self.resource.save()
        self.add_order(self.now - timedelta(days=10))

        self.assertIsNone(self.backfilled())

    def test_keeps_a_recorded_date(self):
        recorded = self.now - timedelta(days=1)
        models.Resource.objects.filter(pk=self.resource.pk).update(
            terminated_at=recorded
        )
        self.add_order(self.now - timedelta(days=10))

        self.assertEqual(self.backfilled(), recorded)
