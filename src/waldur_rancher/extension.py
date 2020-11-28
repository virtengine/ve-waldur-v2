from waldur_core.core import WaldurExtension


class RancherExtension(WaldurExtension):
    class Settings:
        WALDUR_RANCHER = {
            'ROLE_REQUIREMENT': {
                'controllplane': {'CPU': 2, 'RAM': 4096},
                'etcd': {'CPU': 2, 'RAM': 4096},
                'worker': {'CPU': 1, 'RAM': 1024},
            },
            'MOUNT_POINT_CHOICES': (
                '/var/lib/docker',
                '/var/lib/etcd',
                '/opt/media01',
            ),
            'MOUNT_POINT_MIN_SIZE': {'/var/lib/docker': 64, '/var/lib/etcd': 10,},
            'SYSTEM_VOLUME_MIN_SIZE': 64,
            'READ_ONLY_MODE': False,
            'MOUNT_POINT_CHOICE_IS_MANDATORY': False,
            'DISABLE_AUTOMANAGEMENT_OF_USERS': False,
            'DISABLE_SSH_KEY_INJECTION': False,
            'DISABLE_DATA_VOLUME_CREATION': False,
        }

    @staticmethod
    def django_app():
        return 'waldur_rancher'

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
        from datetime import timedelta

        return {
            'waldur-rancher-update-clusters-nodes': {
                'task': 'waldur_rancher.pull_all_clusters_nodes',
                'schedule': timedelta(hours=24),
                'args': (),
            },
            'waldur-rancher-sync-users': {
                'task': 'waldur_rancher.sync_users',
                'schedule': timedelta(hours=24),
                'args': (),
            },
        }

    @staticmethod
    def get_public_settings():
        return [
            'ROLE_REQUIREMENT',
            'MOUNT_POINT_CHOICES',
            'MOUNT_POINT_MIN_SIZE',
            'SYSTEM_VOLUME_MIN_SIZE',
            'READ_ONLY_MODE',
            'MOUNT_POINT_CHOICE_IS_MANDATORY',
            'DISABLE_SSH_KEY_INJECTION',
            'DISABLE_DATA_VOLUME_CREATION',
        ]
