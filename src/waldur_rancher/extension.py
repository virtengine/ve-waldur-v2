from waldur_core.core import WaldurExtension


class RancherExtension(WaldurExtension):

    class Settings:
        WALDUR_RANCHER = {
            'RANCHER_NODE_CLOUD_INIT_TEMPLATE':
                '#cloud-config\n'
                'packages: \n'
                '  - curl\n'
                'runcmd:\n'
                '  - curl -fsSL https://get.docker.com -o get-docker.sh; sh get-docker.sh\n'
                '  - [ sh, -c, "{command}" ]\n',
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
            'MOUNT_POINT_MIN_SIZE': {
                '/var/lib/docker': 64,
                '/var/lib/etcd': 10,
            },
            'SYSTEM_VOLUME_MIN_SIZE': 64,
        }

    @staticmethod
    def django_app():
        return 'waldur_rancher'

    @staticmethod
    def rest_urls():
        from .urls import register_in
        return register_in

    @staticmethod
    def celery_tasks():
        from datetime import timedelta
        return {
            'waldur-rancher-update-node-states': {
                'task': 'waldur_rancher.update_node_states',
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
        ]
