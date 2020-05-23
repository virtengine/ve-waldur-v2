import json
from decimal import ROUND_UP, Decimal
from urllib.parse import urlencode

from dateutil import parser
from django.utils.timezone import get_current_timezone
from rest_framework.test import APIRequestFactory

from waldur_core.core.views import RefreshTokenMixin


def quantize_price(value):
    """
    Returns value rounded up to 2 places after the decimal point.
    :rtype: Decimal
    """
    return value.quantize(Decimal('0.01'), rounding=ROUND_UP)


def get_headers(user):
    """
    It is assumed that localhost is specified in ALLOWED_HOSTS Django setting
    so that internal API requests are allowed.
    """
    token = RefreshTokenMixin().refresh_token(user)
    return dict(
        content_type='application/json',
        HTTP_AUTHORIZATION='Token %s' % token.key,
        SERVER_NAME='localhost',
    )


def get_request(view, user, **extra):
    factory = APIRequestFactory()
    request = factory.get('/', **get_headers(user))
    return view(request, **extra)


def create_request(view, user, post_data, **kwargs):
    factory = APIRequestFactory()
    request = factory.post('/', data=json.dumps(post_data), **get_headers(user))
    return view(request, **kwargs)


def delete_request(view, user, query_params='', **extra):
    factory = APIRequestFactory()
    path = ''
    if query_params:
        path = '?' + urlencode(query_params)
    request = factory.delete(path, **get_headers(user))
    return view(request, **extra)


def parse_datetime(timestr):
    return parser.parse(timestr).replace(tzinfo=get_current_timezone())


def parse_date(timestr):
    return parse_datetime(timestr).date()


def mb_to_gb(value):
    # In marketplace RAM and storage is stored in GB, but in plugin it is stored in MB.
    return quantize_price(Decimal(value / 1024.0))
