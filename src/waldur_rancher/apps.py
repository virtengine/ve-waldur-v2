from django.apps import AppConfig
from django.db.models import signals


class RancherConfig(AppConfig):
    name = 'waldur_rancher'
    verbose_name = 'Rancher'
    service_name = 'Rancher'

    def ready(self):
        from waldur_core.structure import SupportedServices

        from waldur_openstack.openstack_tenant.models import Instance

        from .backend import RancherBackend
        from . import handlers, models, signals as rancher_signals

        SupportedServices.register_backend(RancherBackend)

        rancher_signals.rancher_user_created.connect(
            handlers.notify_create_user,
            sender=models.RancherUser,
            dispatch_uid='waldur_rancher.notify_create_user',
        )

        signals.post_delete.connect(
            handlers.delete_catalog_when_cluster_is_deleted,
            sender=models.Cluster,
            dispatch_uid='waldur_rancher.delete_catalog_when_cluster_is_deleted',
        )

        signals.post_delete.connect(
            handlers.delete_node_if_related_instance_has_been_deleted,
            sender=Instance,
            dispatch_uid='waldur_rancher.delete_node_if_related_instance_has_been_deleted',
        )

        signals.post_delete.connect(
            handlers.delete_cluster_if_all_related_nodes_have_been_deleted,
            sender=models.Node,
            dispatch_uid='waldur_rancher.delete_cluster_if_all_related_nodes_have_been_deleted',
        )

        signals.post_save.connect(
            handlers.set_error_state_for_node_if_related_instance_deleting_is_failed,
            sender=Instance,
            dispatch_uid='waldur_rancher.set_error_state_for_node_if_related_instance_deleting_is_failed',
        )

        signals.post_save.connect(
            handlers.set_error_state_for_cluster_if_related_node_deleting_is_failed,
            sender=models.Node,
            dispatch_uid='waldur_rancher.set_error_state_for_cluster_if_related_node_deleting_is_failed',
        )
