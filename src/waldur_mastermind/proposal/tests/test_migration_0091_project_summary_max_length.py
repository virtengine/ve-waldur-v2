"""Coverage for 0091_proposal_project_summary_max_length.

The migration puts ``max_length`` on ``Proposal.project_summary`` so that every
serializer over the model refuses a summary longer than
``PROJECT_SUMMARY_LENGTH``. The column is a ``TextField`` and stays one: the
limit is a validation rule, not a schema change, and nothing in the database
is touched. Customers upgrade their own deployments, so a summary that is
already longer than the new limit must survive the migration byte for byte;
it is the API, not the migration, that applies the rule from then on (see
``ProposalSummaryLengthTest``).
"""

from importlib import import_module

from django.apps import apps as django_apps
from django.db import connection, models
from django.db.migrations.operations import AlterField
from django.db.migrations.state import ProjectState
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from waldur_mastermind.proposal.models import PROJECT_SUMMARY_LENGTH, Proposal
from waldur_mastermind.proposal.tests import factories

migration = import_module(
    "waldur_mastermind.proposal.migrations.0091_proposal_project_summary_max_length"
)


def _alter_field():
    (operation,) = migration.Migration.operations
    return operation


class ProjectSummaryMaxLengthMigrationTest(TestCase):
    def test_sets_the_limit_the_serializers_enforce(self):
        operation = _alter_field()
        self.assertIsInstance(operation, AlterField)
        self.assertEqual(
            (operation.model_name, operation.name), ("proposal", "project_summary")
        )
        self.assertIsInstance(operation.field, models.TextField)
        self.assertEqual(operation.field.max_length, PROJECT_SUMMARY_LENGTH)
        self.assertEqual(
            Proposal._meta.get_field("project_summary").max_length,
            PROJECT_SUMMARY_LENGTH,
        )

    def test_leaves_existing_rows_and_the_column_alone(self):
        stored = "a" * (PROJECT_SUMMARY_LENGTH + 500)
        proposal = factories.ProposalFactory(project_summary=stored)

        # The state before the migration: the same model with the unbounded
        # column. The graph is absent in CI (--no-migrations), so the states
        # are built from the live models rather than loaded from it. Rendering
        # every model once and cloning keeps the second state to one reload.
        to_state = ProjectState.from_apps(django_apps)
        to_state.apps  # noqa: B018
        from_state = to_state.clone()
        from_state.models["proposal", "proposal"].fields["project_summary"] = (
            models.TextField(blank=True)
        )
        from_state.reload_model("proposal", "proposal")

        with (
            CaptureQueriesContext(connection) as queries,
            connection.schema_editor() as schema_editor,
        ):
            _alter_field().database_forwards(
                "proposal", schema_editor, from_state, to_state
            )
        altering = [q["sql"] for q in queries.captured_queries if "ALTER" in q["sql"]]
        self.assertEqual(altering, [])

        proposal.refresh_from_db()
        self.assertEqual(proposal.project_summary, stored)
