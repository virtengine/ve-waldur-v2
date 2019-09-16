from __future__ import unicode_literals

from django.urls import reverse
from django.contrib.contenttypes import models as ct_models
import factory

from waldur_core.logging import models
# Dependency from `structure` application exists only in tests
from waldur_core.logging.loggers import get_valid_events


class EventFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Event

    message = factory.Sequence(lambda i: 'message#%s' % i)
    event_type = factory.Iterator([
        'first_event',
        'second_event',
        'third_event',
        'fourth_event',
    ])
    context = {
        'customer_abbreviation': 'TCAN',
        'customer_contact_details': 'test details',
        'customer_name': 'Test customer',
        'customer_uuid': 'test_customer_uuid',
        'host': 'example.com',
        'project_name': 'test_project',
        'project_uuid': 'test_project_uuid',
        'user_uuid': 'test_user_uuid',
    }

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('event-list')


class WebHookFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.WebHook

    event_types = get_valid_events()[:3]
    destination_url = 'http://example.com/'

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('webhook-list')

    @classmethod
    def get_url(cls, hook=None):
        if hook is None:
            hook = WebHookFactory()
        return 'http://testserver' + reverse('webhook-detail', kwargs={'uuid': hook.uuid})


class PushHookFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.PushHook

    event_types = get_valid_events()[:3]
    token = 'VALID_TOKEN'
    type = models.PushHook.Type.ANDROID

    @classmethod
    def get_list_url(cls):
        return 'http://testserver' + reverse('pushhook-list')

    @classmethod
    def get_url(cls, hook=None):
        if hook is None:
            hook = PushHookFactory()
        return 'http://testserver' + reverse('pushhook-detail', kwargs={'uuid': hook.uuid})


class SystemNotificationFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.SystemNotification

    event_types = get_valid_events()[:3]
    roles = ['admin']
    hook_content_type = factory.LazyAttribute(
        lambda o: ct_models.ContentType.objects.get_by_natural_key('logging', 'emailhook')
    )
