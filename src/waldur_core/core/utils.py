import calendar
from collections import OrderedDict
import datetime
import functools
import importlib
from itertools import chain
from operator import itemgetter
import os
import re
import time
import unicodedata
import uuid

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import F
from django.db.models.sql.query import get_order_dir
from django.http import QueryDict
from django.template import Context
from django.template.loader import get_template, render_to_string
from django.urls import resolve
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.encoding import force_text
import jwt
from rest_framework.settings import api_settings


def flatten(*xs):
    return tuple(chain.from_iterable(xs))


def sort_dict(unsorted_dict):
    """
    Return a OrderedDict ordered by key names from the :unsorted_dict:
    """
    sorted_dict = OrderedDict()
    # sort items before inserting them into a dict
    for key, value in sorted(unsorted_dict.items(), key=itemgetter(0)):
        sorted_dict[key] = value
    return sorted_dict


def format_time_and_value_to_segment_list(time_and_value_list, segments_count, start_timestamp,
                                          end_timestamp, average=False):
    """
    Format time_and_value_list to time segments

    Parameters
    ^^^^^^^^^^
    time_and_value_list: list of tuples
        Have to be sorted by time
        Example: [(time, value), (time, value) ...]
    segments_count: integer
        How many segments will be in result
    Returns
    ^^^^^^^
    List of dictionaries
        Example:
        [{'from': time1, 'to': time2, 'value': sum_of_values_from_time1_to_time2}, ...]
    """
    segment_list = []
    time_step = (end_timestamp - start_timestamp) / segments_count
    for i in range(segments_count):
        segment_start_timestamp = start_timestamp + time_step * i
        segment_end_timestamp = segment_start_timestamp + time_step
        value_list = [
            value for time, value in time_and_value_list
            if time >= segment_start_timestamp and time < segment_end_timestamp]
        segment_value = sum(value_list)
        if average and len(value_list) != 0:
            segment_value /= len(value_list)

        segment_list.append({
            'from': segment_start_timestamp,
            'to': segment_end_timestamp,
            'value': segment_value,
        })
    return segment_list


def datetime_to_timestamp(datetime):
    return int(time.mktime(datetime.timetuple()))


def timestamp_to_datetime(timestamp, replace_tz=True):
    dt = datetime.datetime.fromtimestamp(int(timestamp))
    if replace_tz:
        dt = dt.replace(tzinfo=timezone.get_current_timezone())
    return dt


def timeshift(**kwargs):
    return timezone.now().replace(microsecond=0) + datetime.timedelta(**kwargs)


def hours_in_month(month=None, year=None):
    now = datetime.datetime.now()
    if not month:
        month = now.month
    if not year:
        year = now.year

    days_in_month = calendar.monthrange(year, month)[1]
    return 24 * days_in_month


def month_start(date):
    return timezone.make_aware(datetime.datetime(day=1, month=date.month, year=date.year))


def month_end(date):
    days_in_month = calendar.monthrange(date.year, date.month)[1]
    last_day_of_month = datetime.date(month=date.month, year=date.year, day=days_in_month)
    last_second_of_month = datetime.datetime.combine(last_day_of_month, datetime.time.max)
    return timezone.make_aware(last_second_of_month, timezone.get_current_timezone())


def pwgen(pw_len=16):
    """ Generate a random password with the given length.
        Allowed chars does not have "I" or "O" or letters and
        digits that look similar -- just to avoid confusion.
    """
    return get_random_string(pw_len, 'abcdefghjkmnpqrstuvwxyz'
                                     'ABCDEFGHJKLMNPQRSTUVWXYZ'
                                     '23456789')


def serialize_instance(instance):
    """ Serialize Django model instance """
    model_name = force_text(instance._meta)
    return '{}:{}'.format(model_name, instance.pk)


def deserialize_instance(serialized_instance):
    """ Deserialize Django model instance """
    model_name, pk = serialized_instance.split(':')
    model = apps.get_model(model_name)
    return model._default_manager.get(pk=pk)


def serialize_class(cls):
    """ Serialize Python class """
    return '{}:{}'.format(cls.__module__, cls.__name__)


def deserialize_class(serilalized_cls):
    """ Deserialize Python class """
    module_name, cls_name = serilalized_cls.split(':')
    module = importlib.import_module(module_name)
    return getattr(module, cls_name)


def clear_url(url):
    """ Remove domain and protocol from url """
    if url.startswith('http'):
        return '/' + url.split('/', 3)[-1]
    return url


def get_model_from_resolve_match(match):
    queryset = match.func.cls.queryset
    if queryset is not None:
        return queryset.model
    else:
        return match.func.cls.model


def instance_from_url(url, user=None):
    """ Restore instance from URL """
    # XXX: This circular dependency will be removed then filter_queryset_for_user
    # will be moved to model manager method
    from waldur_core.structure.managers import filter_queryset_for_user

    url = clear_url(url)
    match = resolve(url)
    model = get_model_from_resolve_match(match)
    queryset = model.objects.all()
    if user is not None:
        queryset = filter_queryset_for_user(model.objects.all(), user)
    return queryset.get(**match.kwargs)


def get_detail_view_name(model):
    if model is NotImplemented:
        raise AttributeError('Cannot get detail view name for not implemented model')

    if hasattr(model, 'get_url_name') and callable(model.get_url_name):
        return '%s-detail' % model.get_url_name()

    return '%s-detail' % model.__name__.lower()


def get_list_view_name(model):
    if model is NotImplemented:
        raise AttributeError('Cannot get list view name for not implemented model')

    if hasattr(model, 'get_url_name') and callable(model.get_url_name):
        return '%s-list' % model.get_url_name()

    return '%s-list' % model.__name__.lower()


def get_fake_context():
    user = get_user_model()()
    request = type('R', (object,), {'method': 'GET', 'user': user, 'query_params': QueryDict()})
    return {'request': request, 'user': user}


def camel_case_to_underscore(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def silent_call(name, *args, **options):
    call_command(name, stdout=open(os.devnull, 'w'), *args, **options)


def format_text(template_name, context):
    template = get_template(template_name).template
    return template.render(Context(context, autoescape=False)).strip()


def send_mail_with_attachment(subject, body, to, from_email=None, html_message=None,
                              filename=None, attachment=None, content_type='text/plain'):
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    email = EmailMultiAlternatives(
        subject=subject,
        body=body,
        to=to,
        from_email=from_email
    )

    if html_message:
        email.attach_alternative(html_message, 'text/html')

    if filename:
        email.attach(filename, attachment, content_type)
    return email.send()


def broadcast_mail(app, event_type, context, recipient_list,
                   filename=None, attachment=None, content_type='text/plain'):
    """
    Shorthand to format email message from template file and sent it to all recipients.

    It is assumed that there are there are 3 templates available for event type in application.
    For example, if app is 'users' and event_type is 'invitation_rejected', then there should be 3 files:

    1) users/invitation_rejected_subject.txt is template for email subject
    2) users/invitation_rejected_message.txt is template for email body as text
    3) users/invitation_rejected_message.html is template for email body as HTML

    By default, built-in Django send_mail is used, all members
    of the recipient list will see the other recipients in the 'To' field.
    Contrary to this, we're using explicit loop in order to ensure that
    recipients would NOT see the other recipients.

    :param app: prefix for template filename.
    :param event_type: postfix for template filename.
    :param context: dictionary passed to the template for rendering.
    :param recipient_list: list of strings, each an email address.
    :param filename: name of the attached file
    :param attachment: content of attachment
    :param content_type: the content type of attachment
    """
    subject_template_name = '%s/%s_subject.txt' % (app, event_type)
    subject = format_text(subject_template_name, context)

    text_template_name = '%s/%s_message.txt' % (app, event_type)
    text_message = format_text(text_template_name, context)

    html_template_name = '%s/%s_message.html' % (app, event_type)
    html_message = render_to_string(html_template_name, context)

    for recipient in recipient_list:
        send_mail_with_attachment(subject, text_message, to=[recipient], html_message=html_message,
                                  filename=filename, attachment=attachment, content_type=content_type)


def get_ordering(request):
    """
    Extract ordering from HTTP request.
    """
    return request.query_params.get(api_settings.ORDERING_PARAM)


def order_with_nulls(queryset, field):
    """
    If sorting order is ascending, then NULL values come first,
    if sorting order is descending, then NULL values come last.
    """
    col, order = get_order_dir(field)
    descending = True if order == 'DESC' else False

    if descending:
        return queryset.order_by(F(col).desc(nulls_last=True))
    else:
        return queryset.order_by(F(col).asc(nulls_first=True))


def is_uuid_like(val):
    """
    Check if value looks like a valid UUID.
    """
    try:
        uuid.UUID(val)
    except (TypeError, ValueError, AttributeError):
        return False
    else:
        return True


def chunks(xs, n):
    """
    Split list to evenly sized chunks

    >> chunks(range(10), 4)
    [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]

    :param xs: arbitrary list
    :param n: chunk size
    :return: list of lists
    """
    return [xs[i:i + n] for i in xrange(0, len(xs), n)]


def create_batch_fetcher(fetcher):
    """
    Decorator to simplify code for chunked fetching.
    It fetches resources from backend API in evenly sized chunks.
    It is needed in order to avoid too long HTTP request error.
    Essentially, it gives the same result as fetcher(items) but does not throw an error.

    :param fetcher: fetcher: function which accepts list of items and returns list of results,
    for example, list of UUIDs and returns list of projects with given UUIDs
    :return: function with the same signature as fetcher
    """
    @functools.wraps(fetcher)
    def wrapped(items):
        """
        :param items: list of items for request, for example, list of UUIDs
        :return: merged list of results
        """
        result = []
        for chunk in chunks(items, settings.WALDUR_CORE['HTTP_CHUNK_SIZE']):
            result.extend(fetcher(chunk))
        return result
    return wrapped


class DryRunCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Don\'t make any changes, instead show what objects would be created.')


def encode_jwt_token(data, api_secret_code=None):
    """
    Encode Python dictionary as JWT token.
    :param data: Dictionary with payload.
    :param api_secret_code: optional string, application secret key is used by default.
    :return: JWT token string with encoded and signed data.
    """
    if api_secret_code is None:
        api_secret_code = settings.SECRET_KEY
    return jwt.encode(data, api_secret_code, algorithm='HS256', json_encoder=DjangoJSONEncoder)


def decode_jwt_token(encoded_data, api_secret_code=None):
    """
    Decode JWT token string to Python dictionary.
    :param encoded_data: JWT token string with encoded and signed data.
    :param api_secret_code: optional string, application secret key is used by default.
    :return: Dictionary with payload.
    """
    if api_secret_code is None:
        api_secret_code = settings.SECRET_KEY
    return jwt.decode(encoded_data, api_secret_code, algorithms=['HS256'])


def normalize_unicode(data):
    return unicodedata.normalize(u'NFKD', data).encode('ascii', 'ignore').decode('utf8')
