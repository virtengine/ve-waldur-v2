from django.apps import AppConfig
from django.conf import settings
from django.db.models import signals


def get_secret_attributes():
    if not settings.WALDUR_OPENSTACK['TENANT_CREDENTIALS_VISIBLE']:
        return 'user_username', 'user_password'


class MarketplaceOpenStackConfig(AppConfig):
    name = 'waldur_mastermind.marketplace_openstack'
    verbose_name = 'Marketplace OpenStack'

    def ready(self):
        from waldur_core.quotas import models as quota_models
        from waldur_core.structure import models as structure_models
        from waldur_core.structure import signals as structure_signals
        from waldur_openstack.openstack import models as openstack_models
        from waldur_openstack.openstack.apps import OpenStackConfig
        from waldur_openstack.openstack_tenant import models as tenant_models
        from waldur_mastermind.invoices import registrators
        from waldur_mastermind.marketplace import models as marketplace_models
        from waldur_mastermind.marketplace import filters as marketplace_filters
        from waldur_mastermind.marketplace import handlers as marketplace_handlers
        from waldur_mastermind.marketplace import signals as marketplace_signals
        from waldur_mastermind.marketplace.plugins import manager
        from waldur_mastermind.marketplace.plugins import Component
        from waldur_mastermind.marketplace_openstack.registrators import MarketplaceItemRegistrator
        from waldur_mastermind.packages import models as package_models

        from . import (
            filters, handlers, processors,
            INSTANCE_TYPE, VOLUME_TYPE, PACKAGE_TYPE,
            RAM_TYPE, CORES_TYPE, STORAGE_TYPE, AVAILABLE_LIMITS
        )

        marketplace_filters.ExternalOfferingFilterBackend.register(filters.VpcExternalFilter())

        signals.post_save.connect(
            handlers.create_offering_from_tenant,
            sender=openstack_models.Tenant,
            dispatch_uid='waldur_mastermind.marketpace_openstack.create_offering_from_tenant',
        )

        signals.pre_delete.connect(
            handlers.archive_offering,
            sender=structure_models.ServiceSettings,
            dispatch_uid='waldur_mastermind.marketpace_openstack.archive_offering',
        )

        resource_models = (tenant_models.Instance, tenant_models.Volume, openstack_models.Tenant)
        marketplace_handlers.connect_resource_metadata_handlers(*resource_models)
        marketplace_handlers.connect_resource_handlers(*resource_models)

        signals.post_save.connect(
            handlers.create_template_for_plan,
            sender=marketplace_models.Plan,
            dispatch_uid='waldur_mastermind.marketpace_openstack.create_template_for_plan',
        )

        signals.post_save.connect(
            handlers.update_template_for_plan,
            sender=marketplace_models.Plan,
            dispatch_uid='waldur_mastermind.marketpace_openstack.update_template_for_plan',
        )

        signals.post_save.connect(
            handlers.update_plan_for_template,
            sender=package_models.PackageTemplate,
            dispatch_uid='waldur_mastermind.marketpace_openstack.update_plan_for_template',
        )

        signals.post_save.connect(
            handlers.synchronize_plan_component,
            sender=marketplace_models.PlanComponent,
            dispatch_uid='waldur_mastermind.marketpace_openstack.synchronize_plan_component',
        )

        FIXED = marketplace_models.OfferingComponent.BillingTypes.FIXED
        manager.register(offering_type=PACKAGE_TYPE,
                         create_resource_processor=processors.PackageCreateProcessor,
                         update_resource_processor=processors.PackageUpdateProcessor,
                         delete_resource_processor=processors.PackageDeleteProcessor,
                         components=(
                             Component(type=RAM_TYPE, name='RAM', measured_unit='GB', billing_type=FIXED),
                             Component(type=CORES_TYPE, name='Cores', measured_unit='cores', billing_type=FIXED),
                             Component(type=STORAGE_TYPE, name='Storage', measured_unit='GB', billing_type=FIXED),
                         ),
                         service_type=OpenStackConfig.service_name,
                         secret_attributes=get_secret_attributes,
                         available_limits=AVAILABLE_LIMITS)

        manager.register(offering_type=INSTANCE_TYPE,
                         create_resource_processor=processors.InstanceCreateProcessor,
                         delete_resource_processor=processors.InstanceDeleteProcessor)

        manager.register(offering_type=VOLUME_TYPE,
                         create_resource_processor=processors.VolumeCreateProcessor,
                         delete_resource_processor=processors.VolumeDeleteProcessor)

        signals.post_save.connect(
            handlers.synchronize_volume_metadata,
            sender=tenant_models.Volume,
            dispatch_uid='waldur_mastermind.marketpace_openstack.synchronize_volume_metadata',
        )

        signals.post_save.connect(
            handlers.synchronize_instance_metadata,
            sender=tenant_models.Instance,
            dispatch_uid='waldur_mastermind.marketpace_openstack.synchronize_instance_metadata',
        )

        signals.post_save.connect(
            handlers.synchronize_internal_ips,
            sender=tenant_models.InternalIP,
            dispatch_uid='waldur_mastermind.marketpace_openstack.synchronize_internal_ips',
        )

        signals.post_save.connect(
            handlers.synchronize_floating_ips,
            sender=tenant_models.FloatingIP,
            dispatch_uid='waldur_mastermind.marketpace_openstack.synchronize_floating_ips',
        )

        signals.post_save.connect(
            handlers.create_resource_of_volume_if_instance_created,
            sender=marketplace_models.Resource,
            dispatch_uid='waldur_mastermind.marketpace_openstack.'
                         'create_resource_of_volume_if_instance_created',
        )

        for model in [tenant_models.Instance, tenant_models.Volume, openstack_models.Tenant]:
            structure_signals.resource_imported.connect(
                handlers.create_marketplace_resource_for_imported_resources,
                sender=model,
                dispatch_uid='waldur_mastermind.marketpace_openstack.'
                             'create_resource_for_imported_%s' % model,
            )

        signals.post_save.connect(
            handlers.import_resource_metadata_when_resource_is_created,
            sender=marketplace_models.Resource,
            dispatch_uid='waldur_mastermind.marketpace_openstack.'
                         'import_resource_metadata_when_resource_is_created',
        )

        signals.post_save.connect(
            handlers.update_openstack_tenant_usages,
            sender=quota_models.Quota,
            dispatch_uid='waldur_mastermind.marketpace_openstack.'
                         'update_openstack_tenant_usages',
        )

        registrators.RegistrationManager.add_registrator(
            marketplace_models.Resource,
            MarketplaceItemRegistrator,
        )

        marketplace_signals.resource_creation_succeeded.connect(
            handlers.update_invoice_when_resource_is_created,
            sender=marketplace_models.Resource,
            dispatch_uid='waldur_mastermind.marketplace.'
                         'update_invoice_when_resource_is_created',
        )

        marketplace_signals.resource_update_succeeded.connect(
            handlers.update_invoice_when_resource_is_updated,
            sender=marketplace_models.Resource,
            dispatch_uid='waldur_mastermind.marketplace.'
                         'update_invoice_when_resource_is_updated',
        )

        marketplace_signals.resource_update_succeeded.connect(
            handlers.update_invoice_when_resource_is_deleted,
            sender=marketplace_models.Resource,
            dispatch_uid='waldur_mastermind.marketplace.'
                         'update_invoice_when_resource_is_deleted',
        )
