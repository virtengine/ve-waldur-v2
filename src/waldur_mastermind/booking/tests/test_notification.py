from django.core import mail
from freezegun import freeze_time
from rest_framework import test

from waldur_core.core import utils as core_utils
from waldur_core.structure.tests import fixtures as structure_fixtures
from waldur_mastermind.marketplace import models as marketplace_models, tasks as marketplace_tasks
from waldur_mastermind.marketplace.tests import factories as marketplace_factories

from .. import PLUGIN_NAME, tasks


class NotificationsTest(test.APITransactionTestCase):
    def setUp(self):
        fixture = structure_fixtures.ProjectFixture()
        offering = marketplace_factories.OfferingFactory(type=PLUGIN_NAME)

        self.order_item = marketplace_factories.OrderItemFactory(
            offering=offering,
            attributes={'schedules': [
                {'start': '2019-01-03T00:00:00.000000Z',
                 'end': '2019-01-05T23:59:59.000000Z'},
            ],
                'name': 'booking'}
        )

        serialized_order = core_utils.serialize_instance(self.order_item.order)
        serialized_user = core_utils.serialize_instance(fixture.staff)
        marketplace_tasks.process_order(serialized_order, serialized_user)

        self.resource = marketplace_models.Resource.objects.filter(name='item_name').exists()

    @freeze_time('2019-01-02')
    def test_send_notification_message_one_day_before_event(self):
        tasks.send_notifications_about_upcoming_bookings()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.order_item.order.created_by.email])
        self.assertEqual(mail.outbox[0].subject, u'Reminder about upcoming booking.')
        self.assertTrue('booking' in mail.outbox[0].body)

    @freeze_time('2019-01-01')
    def test_not_send_notification_message_more_one_day_before_event(self):
        tasks.send_notifications_about_upcoming_bookings()
        self.assertEqual(len(mail.outbox), 0)
