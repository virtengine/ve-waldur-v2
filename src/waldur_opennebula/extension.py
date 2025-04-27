from waldur_core.core import WaldurExtension


class OpenNebulaExtension(WaldurExtension):
    @staticmethod
    def django_app():
        return "waldur_opennebula"

    @staticmethod
    def rest_urls():
        from .urls import register_in
        return register_in

    @staticmethod
    def django_urls():
        from .urls import urlpatterns
        return urlpatterns

    @staticmethod
    def celery_tasks():
        from datetime import timedelta
        return {}

    @staticmethod
    def get_cleanup_executor():
        from .executors import OpenNebulaCleanupExecutor
        return OpenNebulaCleanupExecutor 