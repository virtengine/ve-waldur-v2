import json
from unittest import mock

from ddt import data, ddt
from django.conf import settings
from jira import Issue, User
from jira.resources import IssueType, RequestType
from rest_framework import status

from waldur_core.structure.tests import factories as structure_factories
from waldur_mastermind.marketplace.tests.factories import ResourceFactory
from waldur_mastermind.support.backend.atlassian import ServiceDeskBackend
from waldur_mastermind.support.tests.base import (
    load_resource,
    override_support_settings,
)

from .. import models
from . import base, factories


@ddt
class IssueRetrieveTest(base.BaseTest):
    @data('staff', 'global_support', 'owner')
    def test_user_can_access_customer_issue_if_he_has_customer_level_permission(
        self, user
    ):
        self.client.force_authenticate(getattr(self.fixture, user))
        issue = factories.IssueFactory(customer=self.fixture.customer)

        response = self.client.get(factories.IssueFactory.get_url(issue))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @data('admin', 'manager', 'user')
    def test_user_cannot_access_customer_issue_if_he_has_no_permission(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        issue = factories.IssueFactory(customer=self.fixture.customer)

        response = self.client.get(factories.IssueFactory.get_url(issue))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @data('staff', 'global_support', 'owner', 'admin', 'manager')
    def test_user_can_access_project_issue_if_he_has_project_level_permission(
        self, user
    ):
        self.client.force_authenticate(getattr(self.fixture, user))
        issue = factories.IssueFactory(
            customer=self.fixture.customer, project=self.fixture.project
        )

        response = self.client.get(factories.IssueFactory.get_url(issue))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @data('user')
    def test_user_cannot_access_project_issue_if_he_has_no_project_level_permission(
        self, user
    ):
        self.client.force_authenticate(getattr(self.fixture, user))
        issue = factories.IssueFactory(
            customer=self.fixture.customer, project=self.fixture.project
        )

        response = self.client.get(factories.IssueFactory.get_url(issue))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @data('user')
    def test_user_can_see_a_list_of_all_issues_where_user_is_a_caller(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        issue = factories.IssueFactory(caller=getattr(self.fixture, user))
        url = factories.IssueFactory.get_list_url()

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['key'], issue.key)

    @data('user')
    def test_user_can_not_see_link_to_jira_if_he_is_not_staff_or_support(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        issue = factories.IssueFactory(caller=getattr(self.fixture, user))
        url = factories.IssueFactory.get_url(issue=issue)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('link', response.data)

    @data('staff', 'global_support')
    def test_user_can_see_link_to_jira_if_he_is_staff_or_support(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        issue = factories.IssueFactory(caller=getattr(self.fixture, user))
        url = factories.IssueFactory.get_url(issue=issue)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('link', response.data)

    @override_support_settings(ENABLED=False)
    def test_user_can_not_see_a_list_of_issues_if_support_extension_is_disabled(self):
        self.client.force_authenticate(self.fixture.user)
        url = factories.IssueFactory.get_list_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_424_FAILED_DEPENDENCY)

    def test_marketplace_resource_is_skipped_in_serializer(self):
        self.client.force_authenticate(self.fixture.staff)
        issue = factories.IssueFactory(resource=ResourceFactory())

        response = self.client.get(factories.IssueFactory.get_url(issue))
        self.assertIsNone(response.data['resource_type'])
        self.assertIsNone(response.data['resource'])


class IssueCreateBaseTest(base.BaseTest):
    def setUp(self):
        super(IssueCreateBaseTest, self).setUp()
        self.url = factories.IssueFactory.get_list_url()
        self.caller = structure_factories.UserFactory()

    def _mock_jira(self, old_jira=False, user=None):
        mock.patch.stopall()
        mock_patch = mock.patch('waldur_jira.backend.JIRA')
        self.mock_jira = mock_patch.start()
        self.mock_jira().fields.return_value = json.loads(
            load_resource('jira_fields.json')
        )
        issue_raw = json.loads(load_resource('jira_issue_raw.json'))
        mock_backend_issue = Issue({'server': ''}, None, raw=issue_raw)
        mock_backend_issue.update = mock.MagicMock()
        self.mock_jira().create_customer_request.return_value = mock_backend_issue
        self.mock_jira().waldur_create_customer_request.return_value = (
            mock_backend_issue
        )

        self.mock_jira().create_issue.return_value = mock_backend_issue

        mock_backend_users = [
            User(
                {'server': ''},
                None,
                raw={
                    'key': 'user_1',
                    'active': True,
                    'name': user.email if user else 'user_1@example.com',
                },
            )
        ]
        if old_jira:
            self.mock_jira().search_users.return_value = mock_backend_users
        else:
            self.mock_jira().waldur_search_users.return_value = mock_backend_users

    def _get_valid_payload(self, **additional):
        is_reported_manually = additional.get('is_reported_manually')
        issue_type = settings.WALDUR_SUPPORT['ISSUE']['types'][0]
        factories.RequestTypeFactory(issue_type_name=issue_type)
        payload = {
            'summary': 'test_issue',
            'type': issue_type,
        }

        if is_reported_manually:
            payload['is_reported_manually'] = True
        else:
            payload['caller'] = structure_factories.UserFactory.get_url(
                user=self.caller
            )

        payload.update(additional)
        return payload


@ddt
class IssueCreateTest(IssueCreateBaseTest):
    def setUp(self):
        super(IssueCreateTest, self).setUp()
        factories.SupportCustomerFactory(user=self.caller)

    @data('staff', 'global_support')
    def test_staff_or_support_can_specify_priority(self, user):
        factories.SupportUserFactory(user=getattr(self.fixture, user))
        self.client.force_authenticate(getattr(self.fixture, user))

        priority = factories.PriorityFactory()
        response = self.client.post(
            self.url, data=self._get_valid_payload(priority=priority.name)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['priority'], priority.name)

    @data('admin', 'manager', 'user')
    def test_other_user_can_not_specify_priority(self, user):
        factories.SupportUserFactory(user=getattr(self.fixture, user))
        self.client.force_authenticate(getattr(self.fixture, user))

        priority = factories.PriorityFactory()
        response = self.client.post(
            self.url, data=self._get_valid_payload(priority=priority.name)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @data('staff', 'global_support')
    def test_staff_or_support_can_create_issue_if_he_has_support_user(self, user):
        factories.SupportUserFactory(user=getattr(self.fixture, user))
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.post(self.url, data=self._get_valid_payload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @data('staff', 'global_support')
    def test_staff_or_support_cannot_create_issue_if_he_does_not_have_support_user(
        self, user
    ):
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.post(self.url, data=self._get_valid_payload())

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_create_issue_if_his_support_user_is_disabled(self):
        factories.SupportUserFactory(user=self.fixture.staff, is_active=False)
        self.client.force_authenticate(self.fixture.staff)

        response = self.client.post(self.url, data=self._get_valid_payload())

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @data('staff', 'global_support', 'owner')
    def test_user_with_access_to_customer_can_create_customer_issue(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        payload = self._get_valid_payload(
            customer=structure_factories.CustomerFactory.get_url(self.fixture.customer),
            is_reported_manually=True,
        )

        response = self.client.post(self.url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            models.Issue.objects.filter(summary=payload['summary']).exists()
        )

    @data('admin', 'manager', 'user')
    def test_user_without_access_to_customer_cannot_create_customer_issue(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        payload = self._get_valid_payload(
            customer=structure_factories.CustomerFactory.get_url(self.fixture.customer),
            is_reported_manually=True,
        )

        response = self.client.post(self.url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            models.Issue.objects.filter(summary=payload['summary']).exists()
        )

    @data('staff', 'global_support', 'owner', 'admin', 'manager')
    def test_user_with_access_to_project_can_create_project_issue(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        payload = self._get_valid_payload(
            project=structure_factories.ProjectFactory.get_url(self.fixture.project),
            is_reported_manually=True,
        )

        response = self.client.post(self.url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            models.Issue.objects.filter(summary=payload['summary']).exists()
        )

    @data('user')
    def test_user_without_access_to_project_cannot_create_project_issue(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        payload = self._get_valid_payload(
            project=structure_factories.ProjectFactory.get_url(self.fixture.project),
            is_reported_manually=True,
        )

        response = self.client.post(self.url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            models.Issue.objects.filter(summary=payload['summary']).exists()
        )

    @data('staff', 'global_support', 'owner', 'admin', 'manager')
    def test_user_with_access_to_resource_can_create_resource_issue(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        payload = self._get_valid_payload(
            resource=structure_factories.TestNewInstanceFactory.get_url(
                self.fixture.resource
            ),
            is_reported_manually=True,
        )

        response = self.client.post(self.url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            models.Issue.objects.filter(summary=payload['summary']).exists()
        )

    @data('user')
    def test_user_without_access_to_resource_cannot_create_resource_issue(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        payload = self._get_valid_payload(
            resource=structure_factories.TestNewInstanceFactory.get_url(
                self.fixture.resource
            ),
            is_reported_manually=True,
        )

        response = self.client.post(self.url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            models.Issue.objects.filter(summary=payload['summary']).exists()
        )

    def test_project_issue_populates_customer_field_on_creation(self):
        factories.SupportUserFactory(user=self.fixture.staff)
        self.client.force_authenticate(self.fixture.staff)
        payload = self._get_valid_payload(
            project=structure_factories.ProjectFactory.get_url(self.fixture.project)
        )

        response = self.client.post(self.url, data=payload)

        issue = models.Issue.objects.get(uuid=json.loads(response.content)['uuid'])
        self.assertEqual(issue.customer, self.fixture.project.customer)

    def test_resource_issue_populated_customer_and_project_field_on_creation(self):
        factories.SupportUserFactory(user=self.fixture.staff)
        self.client.force_authenticate(self.fixture.staff)
        payload = self._get_valid_payload(
            resource=structure_factories.TestNewInstanceFactory.get_url(
                self.fixture.resource
            )
        )

        response = self.client.post(self.url, data=payload)

        issue = models.Issue.objects.get(uuid=json.loads(response.content)['uuid'])
        self.assertEqual(
            issue.project, self.fixture.resource.service_project_link.project
        )
        self.assertEqual(
            issue.customer, self.fixture.resource.service_project_link.project.customer
        )

    @override_support_settings(ENABLED=False)
    def test_user_can_not_create_issue_if_support_extension_is_disabled(self):
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.post(self.url, data=self._get_valid_payload())
        self.assertEqual(response.status_code, status.HTTP_424_FAILED_DEPENDENCY)

    def test_fill_custom_fields(self):
        self._mock_jira()

        user = self.fixture.staff
        factories.SupportUserFactory(user=user)
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            data=self._get_valid_payload(
                project=structure_factories.ProjectFactory.get_url(
                    self.fixture.project
                ),
                resource=structure_factories.TestNewInstanceFactory.get_url(),
                template=factories.TemplateFactory.get_url(),
            ),
        )
        issue = response.data
        kwargs = self.mock_jira().create_customer_request.return_value.update.call_args[
            1
        ]
        self.assertEqual(issue['customer_name'], kwargs['field105'])
        self.assertEqual(issue['project_name'], kwargs['field106'])
        self.assertEqual(issue['resource_name'], kwargs['field107'].name)
        self.assertEqual(issue['template'].name, kwargs['field108'])

    def test_if_issue_does_not_have_reporter_organisation_field_not_fill(self):
        self._mock_jira()

        issue = factories.IssueFactory(reporter=None, backend_id=None)
        factories.SupportCustomerFactory(user=issue.caller)
        factories.RequestTypeFactory(issue_type_name=issue.type)
        ServiceDeskBackend().create_issue(issue)
        kwargs = self.mock_jira().create_customer_request.return_value.update.call_args[
            1
        ]
        self.assertTrue('field105' not in kwargs.keys())

    def test_pull_request_types(self):
        self._mock_jira()
        self.mock_jira().request_types.return_value = [
            RequestType(
                {'server': ''},
                None,
                raw={'name': 'Help', 'id': '1', 'issueTypeId': '10101'},
            )
        ]
        self.mock_jira().issue_type.return_value = IssueType(
            {'server': ''}, None, raw={'name': 'Service Request', 'id': '1'}
        )

        issue_type = settings.WALDUR_SUPPORT['ISSUE']['types'][0]
        factories.RequestTypeFactory(issue_type_name=issue_type)
        issue = factories.IssueFactory(reporter=None, backend_id=None, type=issue_type)
        factories.SupportCustomerFactory(user=issue.caller)
        ServiceDeskBackend().create_issue(issue)
        self.assertEqual(models.RequestType.objects.count(), 1)

    def test_create_issue_if_exist_several_backend_users_with_same_email(self):
        self._mock_jira()
        factories.SupportUserFactory(user=self.fixture.staff)
        self.client.force_authenticate(self.fixture.staff)
        mock_backend_users = [
            User({'server': ''}, None, raw={'key': 'user_1', 'active': False}),
            User({'server': ''}, None, raw={'key': 'user_2', 'active': True}),
        ]
        self.mock_jira().search_users.return_value = mock_backend_users
        response = self.client.post(self.url, data=self._get_valid_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_confirmation_comment_if_template_exists(self):
        payload = self._get_valid_payload()
        issue_type = payload['type']
        factories.TemplateConfirmationCommentFactory(
            issue_type=issue_type, template='issue_type template'
        )
        self._create_confirmation_comment('issue_type template')

    def test_create_confirmation_comment_if_only_default_template_exists(self):
        factories.TemplateConfirmationCommentFactory(template='default template')
        self._create_confirmation_comment('default template')

    def test_do_not_create_confirmation_comment_if_template_does_not_exist(self):
        self._create_confirmation_comment(None)

    def _create_confirmation_comment(self, expected_body):
        user = self.fixture.staff
        factories.SupportUserFactory(user=user)
        mock.patch.stopall()
        with mock.patch(
            'waldur_mastermind.support.backend.atlassian.ServiceDeskBackend.create_issue'
        ):
            with mock.patch(
                'waldur_mastermind.support.backend.atlassian.ServiceDeskBackend._add_comment'
            ) as _add_comment:
                self.client.force_authenticate(user)
                self.client.post(self.url, data=self._get_valid_payload())
                if expected_body:
                    _add_comment.assert_called_once_with(
                        None, expected_body, is_internal=False
                    )
                else:
                    _add_comment.assert_not_called()


@override_support_settings(USE_OLD_API=True)
class IssueCreateOldAPITest(IssueCreateBaseTest):
    def setUp(self):
        super(IssueCreateOldAPITest, self).setUp()
        self._mock_jira(old_jira=True, user=self.fixture.staff)

    def test_identification_from_email_if_caller_does_not_exist(self):
        user = self.fixture.staff
        self.client.force_authenticate(user)
        self.client.post(
            self.url, data=self._get_valid_payload(is_reported_manually=True)
        )
        kwargs = self.mock_jira().waldur_create_customer_request.call_args[0][0]
        self.assertEqual(user.email, kwargs['requestParticipants'][0])


@ddt
class IssueUpdateTest(base.BaseTest):
    def setUp(self):
        super(IssueUpdateTest, self).setUp()
        self.issue = factories.IssueFactory(
            customer=self.fixture.customer, project=self.fixture.project
        )
        self.url = factories.IssueFactory.get_url(self.issue)

    @data('staff', 'global_support')
    def test_staff_or_support_can_edit_issue(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        payload = self._get_valid_payload()

        response = self.client.patch(self.url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            models.Issue.objects.filter(summary=payload['summary']).exists()
        )

    @data('owner', 'admin', 'manager')
    def test_nonstaff_user_cannot_edit_issue(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        payload = self._get_valid_payload()

        response = self.client.patch(self.url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            models.Issue.objects.filter(summary=payload['summary']).exists()
        )

    @override_support_settings(ENABLED=False)
    def test_staff_can_not_update_issue_if_support_extension_is_disabled(self):
        self.client.force_authenticate(self.fixture.staff)
        payload = self._get_valid_payload()
        response = self.client.patch(self.url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_424_FAILED_DEPENDENCY)

    def _get_valid_payload(self):
        return {'summary': 'edited_summary'}


@ddt
class IssueDeleteTest(base.BaseTest):
    def setUp(self):
        super(IssueDeleteTest, self).setUp()
        self.issue = factories.IssueFactory(
            customer=self.fixture.customer, project=self.fixture.project
        )
        self.url = factories.IssueFactory.get_url(self.issue)

    @data('staff', 'global_support')
    def test_staff_or_support_can_delete_issue(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(models.Issue.objects.filter(id=self.issue.id).exists())

    @data('owner', 'admin', 'manager')
    def test_nonstaff_user_cannot_delete_issue(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(models.Issue.objects.filter(id=self.issue.id).exists())

    @override_support_settings(ENABLED=False)
    def test_user_can_not_delete_issue_if_support_extension_is_disabled(self):
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_424_FAILED_DEPENDENCY)

    def test_user_can_not_delete_issue_if_related_offering_exists(self):
        factories.OfferingFactory(issue=self.issue)
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@ddt
class IssueCommentTest(base.BaseTest):
    @data('staff', 'global_support', 'owner', 'admin', 'manager')
    def test_user_with_access_to_issue_can_comment(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        issue = factories.IssueFactory(
            customer=self.fixture.customer, project=self.fixture.project
        )
        payload = self._get_valid_payload()

        response = self.client.post(
            factories.IssueFactory.get_url(issue, action='comment'), data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            models.Comment.objects.filter(
                issue=issue, description=payload['description']
            )
        )

    @data('owner', 'admin', 'manager', 'user')
    def test_user_can_comment_on_issue_where_he_is_caller_without_project_and_customer(
        self, user
    ):
        current_user = getattr(self.fixture, user)
        self.client.force_authenticate(current_user)
        issue = factories.IssueFactory(caller=current_user, project=None)
        payload = self._get_valid_payload()

        response = self.client.post(
            factories.IssueFactory.get_url(issue, action='comment'), data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            models.Comment.objects.filter(
                issue=issue, description=payload['description']
            )
        )

    @data('admin', 'manager', 'user')
    def test_user_without_access_to_instance_cannot_comment(self, user):
        self.client.force_authenticate(getattr(self.fixture, user))
        issue = factories.IssueFactory(customer=self.fixture.customer)
        payload = self._get_valid_payload()

        response = self.client.post(
            factories.IssueFactory.get_url(issue, action='comment'), data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            models.Comment.objects.filter(
                issue=issue, description=payload['description']
            )
        )

    @override_support_settings(ENABLED=False)
    def test_user_can_not_comment_issue_if_support_extension_is_disabled(self):
        self.client.force_authenticate(self.fixture.staff)
        issue = factories.IssueFactory(customer=self.fixture.customer)
        payload = self._get_valid_payload()

        response = self.client.post(
            factories.IssueFactory.get_url(issue, action='comment'), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_424_FAILED_DEPENDENCY)

    def _get_valid_payload(self):
        return {'description': 'Comment description'}
