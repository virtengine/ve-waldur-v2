from waldur_core.core import WaldurExtension


class OpenNebulaExtension(WaldurExtension):
    @staticmethod
    def django_app():
        return "waldur_opennebula"
    
    @staticmethod
    def is_assembly():
        return False
    
    @staticmethod
    def get_url_prefix():
        return 'opennebula'
    
    @staticmethod
    def rest_urls():
        from .urls import register_in
        return register_in

    @staticmethod
    def django_urls():
        from .urls import urlpatterns
        return urlpatterns
    
    @staticmethod
    def settings_serializer():
        # register your ServiceOptionsSerializer so the “Providers” dropdown
        # in Admin picks up OpenNebula
        from .serializers import OpenNebulaServiceSerializer
        return OpenNebulaServiceSerializer

    @staticmethod
    def celery_tasks():
        from datetime import timedelta

        return {
            'opennebula-tenant-pull': {
                'task': 'opennebula.pull_tenants_task',
                'schedule': timedelta(hours=12),
                'args': (),
            },
        }

    @staticmethod
    def get_cleanup_executor():
        from .executors import OpenNebulaCleanupExecutor
        return OpenNebulaCleanupExecutor 