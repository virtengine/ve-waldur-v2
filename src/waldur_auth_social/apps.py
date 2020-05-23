from django.apps import AppConfig
from django.conf import settings
from django.db.models import signals


class AuthSocialConfig(AppConfig):
    name = 'waldur_auth_social'
    # Label is derived from Waldur Plus to avoid data migration
    label = 'nodeconductor_auth'
    verbose_name = 'Auth Social'

    def ready(self):
        from . import handlers

        signals.post_save.connect(
            handlers.create_auth_profile,
            sender=settings.AUTH_USER_MODEL,
            dispatch_uid='waldur_auth_social.handlers.create_auth_profile',
        )
