# Django test settings for Waldur Core.
from waldur_core.server.doc_settings import *  # noqa: F403

MEDIA_ROOT = '/tmp/'  # noqa: S108

INSTALLED_APPS += (  # noqa: F405
    'waldur_core.quotas.tests',
    'waldur_core.structure.tests',
    'waldur_pid.tests',
)

ROOT_URLCONF = 'waldur_core.structure.tests.urls'

DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'waldur',}}

ALLOWED_HOSTS = ['localhost']
