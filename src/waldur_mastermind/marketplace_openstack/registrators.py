import decimal

from django.conf import settings

from waldur_mastermind.common.utils import mb_to_gb
from waldur_mastermind.invoices import models as invoices_models
from waldur_mastermind.invoices.registrators import BaseRegistrator
from waldur_mastermind.marketplace import models
from waldur_mastermind.marketplace_openstack import (
    CORES_TYPE,
    PACKAGE_TYPE,
    RAM_TYPE,
    STORAGE_TYPE,
)


class MarketplaceItemRegistrator(BaseRegistrator):
    def get_customer(self, source):
        return source.project.customer

    def get_sources(self, customer):
        if not settings.WALDUR_MARKETPLACE_OPENSTACK['BILLING_ENABLED']:
            return models.Resource.objects.none()

        return models.Resource.objects.filter(
            project__customer=customer, offering__type=PACKAGE_TYPE
        ).exclude(
            state__in=[
                models.Resource.States.CREATING,
                models.Resource.States.TERMINATED,
            ]
        )

    def _create_item(self, source, invoice, start, end):
        from waldur_mastermind.marketplace import plugins

        details = self.get_details(source)
        builtin_components = plugins.manager.get_components(source.offering.type)
        component_factors = {c.type: c.factor for c in builtin_components}
        unit_price = sum(
            decimal.Decimal(source.limits.get(component.component.type, 0))
            * component.price
            / decimal.Decimal(component_factors.get(component.component.type, 1))
            for component in source.plan.components.all()
        )

        start = invoices_models.adjust_invoice_items(
            invoice, source, start, unit_price, source.plan.unit
        )

        item = invoices_models.InvoiceItem.objects.create(
            scope=source,
            project=source.project,
            unit_price=unit_price,
            unit=source.plan.unit,
            product_code=source.plan.product_code,
            article_code=source.plan.article_code,
            invoice=invoice,
            start=start,
            end=end,
            details=details,
        )
        self.init_details(item)

    def format_storage_description(self, source):
        if STORAGE_TYPE in source.limits:
            return '{disk} GB storage'.format(
                disk=int(mb_to_gb(source.limits.get(STORAGE_TYPE, 0)))
            )
        else:
            parts = []
            for (k, v) in source.limits.items():
                if k.startswith('gigabytes_') and v:
                    parts.append(
                        '{size} GB {type} storage'.format(
                            size=int(v), type=k.replace('gigabytes_', '')
                        )
                    )
            return ' - '.join(parts)

    def get_name(self, source):
        return '{resource} ({offering} / VPC {cores} CPU - {ram} GB RAM - {storage})'.format(
            resource=source.name,
            offering=source.offering.name,
            cores=int(source.limits.get(CORES_TYPE, 0)),
            ram=int(mb_to_gb(source.limits.get(RAM_TYPE, 0))),
            storage=self.format_storage_description(source),
        )
