from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


class IncorrectStateException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _('Cannot modify an object in its current state.')


class RuntimeStateException(Exception):
    pass


class ExtensionDisabled(APIException):
    status_code = status.HTTP_424_FAILED_DEPENDENCY
    default_detail = _('Extension is disabled.')
