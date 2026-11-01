from django.contrib import admin
from django.forms.models import model_to_dict
from django.test import RequestFactory, TestCase

from waldur_core.structure.tests import factories as structure_factories
from waldur_mastermind.proposal import models
from waldur_mastermind.proposal.admin import ProposalAdmin
from waldur_mastermind.proposal.models import PROJECT_SUMMARY_LENGTH
from waldur_mastermind.proposal.tests import factories


class ProposalAdminTest(TestCase):
    """The summary limit is an API rule for new input; a proposal stored over
    it before the limit existed must still be saveable from the admin, and a
    TextField's max_length would otherwise become a validator on its form."""

    def _admin_form(self, proposal):
        request = RequestFactory().get("/")
        request.user = structure_factories.UserFactory(is_staff=True)
        form_class = ProposalAdmin(models.Proposal, admin.site).get_form(
            request, proposal
        )
        data = {k: "" if v is None else v for k, v in model_to_dict(proposal).items()}
        return form_class(data=data, instance=proposal)

    def test_summary_over_limit_does_not_block_the_admin_form(self):
        proposal = factories.ProposalFactory(
            project_summary="a" * (PROJECT_SUMMARY_LENGTH + 500)
        )
        form = self._admin_form(proposal)
        form.is_valid()
        self.assertNotIn("project_summary", form.errors)

    def test_description_limit_still_applies_in_the_admin_form(self):
        # The description column is bounded, so its limit is the schema's and
        # stays on the form.
        proposal = factories.ProposalFactory()
        form = self._admin_form(proposal)
        self.assertEqual(form.fields["description"].max_length, 4096)
        self.assertIsNone(form.fields["project_summary"].max_length)
