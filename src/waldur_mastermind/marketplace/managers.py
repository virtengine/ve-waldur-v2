from django.contrib.contenttypes.models import ContentType
from django.db import models as django_models
from django.db.models import Q

from waldur_core.core import managers as core_managers
from waldur_core.structure import models as structure_models


class MixinManager(core_managers.GenericKeyMixin, django_models.Manager):
    pass


class OfferingQuerySet(django_models.QuerySet):
    def filter_for_user(self, user):
        if user.is_anonymous or user.is_staff or user.is_support:
            return self

        connected_customers = set(
            structure_models.Customer.objects.all()
            .filter(
                Q(permissions__user=user, permissions__is_active=True)
                | Q(
                    projects__permissions__user=user,
                    projects__permissions__is_active=True,
                )
            )
            .distinct()
        )

        return self.filter(
            Q(shared=True)
            | Q(shared=False, allowed_customers__in=connected_customers)
            | Q(shared=False, customer__in=connected_customers)
        )

    def filter_for_customer(self, value):
        return self.filter(
            Q(shared=True) | Q(customer__uuid=value) | Q(allowed_customers__uuid=value)
        )

    def filter_for_project(self, value):
        settings_ct = ContentType.objects.get_for_model(
            structure_models.ServiceSettings
        )
        service_settings = {
            pk
            for spl in structure_models.ServiceProjectLink.get_all_models()
            for pk in spl.objects.filter(project__uuid=value).values_list(
                'service__settings_id', flat=True
            )
        }

        return self.filter(
            Q(content_type=settings_ct, object_id__in=service_settings)
            | ~Q(content_type=settings_ct)
        )

    def filter_importable(self, user):
        # Import is limited to staff for shared offerings and to staff/owners for private offerings

        if user.is_staff:
            return self

        owned_customers = set(
            structure_models.Customer.objects.all()
            .filter(
                permissions__user=user,
                permissions__is_active=True,
                permissions__role=structure_models.CustomerRole.OWNER,
            )
            .distinct()
        )

        return self.filter(
            Q(shared=False, allowed_customers__in=owned_customers)
            | Q(shared=False, customer__in=owned_customers)
        )


class OfferingManager(MixinManager):
    def get_queryset(self):
        return OfferingQuerySet(self.model, using=self._db)
