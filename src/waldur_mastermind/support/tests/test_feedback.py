import mock
from ddt import data, ddt
from django.core import mail, signing
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from waldur_core.core import utils as core_utils

from .. import models, tasks
from ..backend.atlassian import ServiceDeskBackend
from . import base, factories


@ddt
class FeedbackCreateTest(base.BaseTest):
    @data(
        'staff', 'owner', 'admin', 'manager', 'user', '',
    )
    def test_user_can_create_feedback(self, user):
        url = factories.FeedbackFactory.get_list_url()
        issue = factories.IssueFactory()
        signer = signing.TimestampSigner()
        token = signer.sign(issue.uuid.hex)

        if user:
            self.client.force_authenticate(getattr(self.fixture, user))

        response = self.client.post(
            url,
            data={'evaluation': models.Feedback.Evaluation.POSITIVE, 'token': token},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_comment_has_been_created_if_feedback_has_been_synchronized(self):
        with mock.patch.object(ServiceDeskBackend, 'create_comment'):
            backend = ServiceDeskBackend()
            feedback = factories.FeedbackFactory(comment='Test Feedback', evaluation=0)
            backend.create_feedback(feedback)
            self.assertTrue(
                models.Feedback.objects.filter(issue=feedback.issue).exists()
            )

    def test_user_cannot_create_feedback_if_token_is_wrong(self):
        url = factories.FeedbackFactory.get_list_url()
        token = 'token'

        response = self.client.post(
            url,
            data={'evaluation': models.Feedback.Evaluation.POSITIVE, 'token': token},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_create_feedback_if_it_already_exists(self):
        url = factories.FeedbackFactory.get_list_url()
        feedback = factories.FeedbackFactory()
        issue = feedback.issue
        signer = signing.TimestampSigner()
        token = signer.sign(issue.uuid.hex)

        response = self.client.post(
            url,
            data={'evaluation': models.Feedback.Evaluation.POSITIVE, 'token': token},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FeedbackNotificationTest(base.BaseTest):
    @mock.patch(
        'waldur_mastermind.support.handlers.tasks.send_issue_feedback_notification'
    )
    @override_settings(ISSUE_FEEDBACK_ENABLE=True)
    def test_feedback_notification(self, mock_tasks):
        factories.IssueStatusFactory(
            name='resolved', type=models.IssueStatus.Types.RESOLVED
        )
        factories.IssueStatusFactory(
            name='canceled', type=models.IssueStatus.Types.CANCELED
        )
        issue = factories.IssueFactory()
        issue.set_resolved()
        serialized_issue = core_utils.serialize_instance(issue)
        mock_tasks.delay.assert_called_once_with(serialized_issue)

    def test_feedback_notification_text(self):
        issue = factories.IssueFactory()
        serialized_issue = core_utils.serialize_instance(issue)
        tasks.send_issue_feedback_notification(serialized_issue)
        self.assertEqual(len(mail.outbox), 1)


@ddt
class FeedbackReportTest(base.BaseTest):
    def setUp(self):
        super(FeedbackReportTest, self).setUp()
        factories.FeedbackFactory(evaluation=models.Feedback.Evaluation.POSITIVE)
        factories.FeedbackFactory(evaluation=models.Feedback.Evaluation.NEGATIVE)
        self.avg = round(
            (models.Feedback.Evaluation.POSITIVE + models.Feedback.Evaluation.NEGATIVE)
            / 2,
            2,
        )

    @data(
        'staff', 'global_support',
    )
    def test_user_can_get_report(self, user):
        if user:
            self.client.force_authenticate(getattr(self.fixture, user))
            url_report = reverse('support-feedback-report')
            response = self.client.get(url_report)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data, {'Positive': 1, 'Negative': 1})

            url_average = reverse('support-feedback-average-report')
            response = self.client.get(url_average)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data, self.avg)

    @data(
        'owner', 'admin', 'manager', 'user', '',
    )
    def test_user_can_not_get_report(self, user):
        if user:
            self.client.force_authenticate(getattr(self.fixture, user))
            url_report = reverse('support-feedback-report')
            response = self.client.get(url_report)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            url_average = reverse('support-feedback-average-report')
            response = self.client.get(url_average)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
