from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from waldur_core.core.fields import NaturalChoiceField
from waldur_core.core.serializers import RestrictedSerializerMixin
from waldur_core.logging import models, loggers


class EventSerializer(RestrictedSerializerMixin,
                      serializers.ModelSerializer):
    context = serializers.JSONField(read_only=True)

    class Meta(object):
        model = models.Event
        fields = ('uuid', 'created', 'event_type', 'message', 'context')


class BaseHookSerializer(serializers.HyperlinkedModelSerializer):
    author_uuid = serializers.ReadOnlyField(source='user.uuid')
    hook_type = serializers.SerializerMethodField()

    class Meta(object):
        model = models.BaseHook

        fields = (
            'url', 'uuid', 'is_active', 'author_uuid',
            'event_types', 'event_groups', 'created', 'modified',
            'hook_type'
        )

        extra_kwargs = {
            'url': {'lookup_field': 'uuid'},
        }

    def get_fields(self):
        """
        When static declaration is used, event type choices are fetched too early -
        even before all apps are initialized. As a result, some event types are missing.
        When dynamic declaration is used, all valid event types are available as choices.
        """
        fields = super(BaseHookSerializer, self).get_fields()
        fields['event_types'] = serializers.MultipleChoiceField(
            choices=loggers.get_valid_events(), required=False)
        fields['event_groups'] = serializers.MultipleChoiceField(
            choices=loggers.get_event_groups_keys(), required=False)
        return fields

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super(BaseHookSerializer, self).create(validated_data)

    def validate(self, attrs):
        if not self.instance and 'event_types' not in attrs and 'event_groups' not in attrs:
            raise serializers.ValidationError(_('Please specify list of event_types or event_groups.'))

        if 'event_groups' in attrs:
            events = list(attrs.get('event_types', []))
            groups = list(attrs.get('event_groups', []))
            events = sorted(set(loggers.expand_event_groups(groups)) | set(events))

            attrs['event_types'] = events
            attrs['event_groups'] = groups

        elif 'event_types' in attrs:
            attrs['event_types'] = list(attrs['event_types'])

        return attrs

    def get_hook_type(self, hook):
        raise NotImplementedError


class SummaryHookSerializer(serializers.Serializer):

    def to_representation(self, instance):
        serializer = self.get_hook_serializer(instance.__class__)
        return serializer(instance, context=self.context).data

    def get_hook_serializer(self, cls):
        for serializer in BaseHookSerializer.__subclasses__():
            if serializer.Meta.model == cls:
                return serializer
        raise ValueError('Hook serializer for %s class is not found' % cls)


class WebHookSerializer(BaseHookSerializer):
    content_type = NaturalChoiceField(models.WebHook.ContentTypeChoices.CHOICES, required=False)

    class Meta(BaseHookSerializer.Meta):
        model = models.WebHook
        fields = BaseHookSerializer.Meta.fields + ('destination_url', 'content_type')

    def get_hook_type(self, hook):
        return 'webhook'


class PushHookSerializer(BaseHookSerializer):
    type = NaturalChoiceField(models.PushHook.Type.CHOICES)

    class Meta(BaseHookSerializer.Meta):
        model = models.PushHook
        fields = BaseHookSerializer.Meta.fields + ('type', 'device_id', 'token', 'device_manufacturer', 'device_model')

    def get_hook_type(self, hook):
        return 'pushhook'


class EmailHookSerializer(BaseHookSerializer):

    class Meta(BaseHookSerializer.Meta):
        model = models.EmailHook
        fields = BaseHookSerializer.Meta.fields + ('email', )

    def get_hook_type(self, hook):
        return 'email'
