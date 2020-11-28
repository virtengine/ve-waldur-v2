from datetime import timedelta

from waldur_core.core import WaldurExtension


class PayPalExtension(WaldurExtension):
    class Settings:
        WALDUR_PAYPAL = {
            'ENABLED': False,
            'BACKEND': {
                'mode': 'sandbox',  # either 'live' or 'sandbox'
                'client_id': '',
                'client_secret': '',
                'currency_name': 'USD',
            },
            'STALE_PAYMENTS_LIFETIME': timedelta(weeks=1),
        }

    @staticmethod
    def django_app():
        return 'waldur_paypal'

    @staticmethod
    def django_urls():
        from .urls import urlpatterns

        return urlpatterns

    @staticmethod
    def rest_urls():
        from .urls import register_in

        return register_in

    @staticmethod
    def celery_tasks():
        return {
            'payments-cleanup': {
                'task': 'waldur_paypal.PaymentsCleanUp',
                'schedule': timedelta(hours=24),
                'args': (),
            },
            'send-invoices': {
                'task': 'waldur_paypal.SendInvoices',
                'schedule': timedelta(hours=24),
                'args': (),
            },
        }
