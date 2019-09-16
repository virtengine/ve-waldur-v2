from __future__ import unicode_literals

import logging
import six

from waldur_mastermind.invoices import registrators
from waldur_mastermind.invoices import models as invoice_models
from waldur_mastermind.marketplace import utils as marketplace_utils
from waldur_slurm import models as slurm_models

from . import models, utils

logger = logging.getLogger(__name__)


class AllocationRegistrator(registrators.BaseRegistrator):
    def get_sources(self, customer):
        return slurm_models.Allocation.objects.filter(service_project_link__project__customer=customer).distinct()

    def get_customer(self, source):
        return source.service_project_link.project.customer

    def _create_item(self, source, invoice, start, end):
        allocation = source
        package = self.get_package(allocation)
        if package:
            item = invoice_models.InvoiceItem.objects.create(
                scope=allocation,
                project=source.service_project_link.project,
                unit_price=utils.get_deposit_usage(allocation, package),
                unit=invoice_models.InvoiceItem.Units.QUANTITY,
                quantity=1,
                product_code=package.product_code,
                article_code=package.article_code,
                invoice=invoice,
                start=start,
                end=end,
            )
            self.init_details(item)
            return item

    def get_package(self, allocation):
        service_settings = allocation.service_project_link.service.settings
        try:
            return models.SlurmPackage.objects.get(service_settings=service_settings)
        except models.SlurmPackage.DoesNotExist:
            logger.debug('Skip SLURM invoice item because pricing package'
                         ' for service settings %s is not defined.', service_settings)

    def get_details(self, source):
        details = {
            'cpu_usage': source.cpu_usage,
            'gpu_usage': source.gpu_usage,
            'ram_usage': source.ram_usage,
            'deposit_usage': six.text_type(source.deposit_usage),
            'scope_uuid': source.uuid.hex,
        }
        service_provider_info = marketplace_utils.get_service_provider_info(source)
        details.update(service_provider_info)
        return details
