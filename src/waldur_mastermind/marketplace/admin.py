from django.conf.urls import url
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import ModelForm
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext
from modeltranslation import admin as modeltranslation_admin

from waldur_core.core import admin as core_admin
from waldur_core.core import utils as core_utils
from waldur_core.core.admin import (
    ExecutorAdminAction,
    JsonWidget,
    PasswordWidget,
    format_json_field,
)
from waldur_core.core.admin_filters import RelatedOnlyDropdownFilter
from waldur_core.structure.models import (
    PrivateServiceSettings,
    ServiceSettings,
    SharedServiceSettings,
)
from waldur_mastermind.google.models import GoogleCredentials
from waldur_mastermind.marketplace_openstack import (
    executors as marketplace_openstack_executors,
)
from waldur_pid import tasks as pid_tasks
from waldur_pid import utils as pid_utils

from . import executors, models, tasks


class GoogleCredentialsAdminForm(ModelForm):
    class Meta:
        widgets = {
            'client_secret': PasswordWidget(),
            'calendar_token': PasswordWidget(),
            'calendar_refresh_token': PasswordWidget(),
        }


class GoogleCredentialsInline(admin.StackedInline):
    model = GoogleCredentials
    form = GoogleCredentialsAdminForm


class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'customer', 'created')
    inlines = [GoogleCredentialsInline]


class AttributeOptionInline(admin.TabularInline):
    model = models.AttributeOption


class AttributeAdmin(admin.ModelAdmin):
    inlines = [AttributeOptionInline]
    list_display = (
        'title',
        'get_category',
        'section',
        'type',
        'key',
        'required',
    )
    list_filter = ('section',)
    ordering = ('section', 'title')

    def get_category(self, obj):
        return obj.section.category

    get_category.short_description = _('Category')
    get_category.admin_order_field = 'section__category__title'


class AttributeInline(admin.TabularInline):
    model = models.Attribute


class SectionAdmin(admin.ModelAdmin):
    inlines = [AttributeInline]
    list_display = ('title', 'category', 'key')


class SectionInline(admin.TabularInline):
    model = models.Section


class CategoryColumnInline(admin.TabularInline):
    model = models.CategoryColumn
    list_display = ('index', 'title', 'attribute', 'widget')


class CategoryComponentInline(admin.TabularInline):
    model = models.CategoryComponent


class CategoryAdmin(modeltranslation_admin.TranslationAdmin):
    list_display = (
        'title',
        'uuid',
    )
    inlines = [SectionInline, CategoryColumnInline, CategoryComponentInline]


class ScreenshotsInline(admin.StackedInline):
    model = models.Screenshot
    classes = ['collapse']
    fields = ('name', 'description', 'image')
    extra = 1


class PlansInline(admin.StackedInline):
    model = models.Plan
    classes = ['collapse']
    fields = (
        'name',
        'description',
        'unit_price',
        'unit',
        'product_code',
        'article_code',
        'archived',
        'max_amount',
    )
    extra = 1


class ConnectedResourceMixin:
    """
    Protects object from modification if there are connected resources.
    """

    protected_fields = ()

    def get_readonly_fields(self, request, obj=None):
        fields = super(ConnectedResourceMixin, self).get_readonly_fields(request, obj)
        if obj and obj.has_connected_resources:
            return fields + self.protected_fields
        else:
            return fields

    def has_delete_permission(self, request, obj=None):
        if request.user.is_staff:
            return True
        if obj and obj.has_connected_resources:
            return False
        return True


class ParentInlineMixin:
    def get_parent_object_from_request(self, request):
        """
        Returns the parent object from the request or None.

        Note that this only works for Inlines, because the `parent_model`
        is not available in the regular admin.ModelAdmin as an attribute.
        """
        resolved = resolve(request.path_info)
        if resolved.args:
            return self.parent_model.objects.get(pk=resolved.args[0])
        return None


class PlanComponentInline(
    ConnectedResourceMixin, ParentInlineMixin, admin.TabularInline
):
    model = models.PlanComponent
    classes = ['collapse']
    protected_fields = ('component', 'amount', 'price')

    def has_add_permission(self, request, obj=None):
        plan = self.get_parent_object_from_request(request)
        if plan and plan.has_connected_resources:
            return False
        else:
            return True

    def get_extra(self, request, obj=None, **kwargs):
        plan = self.get_parent_object_from_request(request)
        if plan and plan.has_connected_resources:
            return 0
        else:
            return super(PlanComponentInline, self).get_extra(request, obj, **kwargs)


class PlanAdmin(ConnectedResourceMixin, admin.ModelAdmin):
    list_display = ('name', 'offering', 'archived', 'unit', 'unit_price')
    list_filter = ('offering', 'archived')
    search_fields = ('name', 'offering__name')
    inlines = [PlanComponentInline]
    protected_fields = ('unit', 'unit_price', 'product_code', 'article_code')
    readonly_fields = ('scope_link', 'backend_id')
    fields = (
        'name',
        'description',
        'unit',
        'unit_price',
        'product_code',
        'article_code',
        'max_amount',
        'archived',
    ) + readonly_fields

    def scope_link(self, obj):
        return get_admin_link_for_scope(obj.scope)

    scope_link.short_description = 'Scope'


class OfferingAdminForm(ModelForm):
    class Meta:
        widgets = {
            'attributes': JsonWidget(),
            'options': JsonWidget(),
            'secret_options': JsonWidget(),
            'plugin_options': JsonWidget(),
            'referrals': JsonWidget(),
        }


class OfferingComponentInline(admin.StackedInline):
    model = models.OfferingComponent
    classes = ['collapse']
    extra = 1


def get_admin_url_for_scope(scope):
    if isinstance(scope, ServiceSettings):
        model = scope.shared and SharedServiceSettings or PrivateServiceSettings
    else:
        model = scope
    return reverse(
        'admin:%s_%s_change' % (scope._meta.app_label, model._meta.model_name),
        args=[scope.id],
    )


def get_admin_link_for_scope(scope):
    return format_html('<a href="{}">{}</a>', get_admin_url_for_scope(scope), scope)


class OfferingAdmin(admin.ModelAdmin):
    form = OfferingAdminForm
    inlines = [ScreenshotsInline, PlansInline, OfferingComponentInline]
    list_display = ('name', 'uuid', 'customer', 'state', 'category', 'billable')
    list_filter = (
        'state',
        'shared',
        'billable',
        ('category', RelatedOnlyDropdownFilter),
    )
    search_fields = ('name', 'uuid')
    fields = (
        'state',
        'customer',
        'category',
        'name',
        'native_name',
        'description',
        'native_description',
        'full_description',
        'rating',
        'thumbnail',
        'attributes',
        'options',
        'plugin_options',
        'secret_options',
        'shared',
        'billable',
        'allowed_customers',
        'type',
        'scope_link',
        'vendor_details',
        'paused_reason',
        'datacite_doi',
        'citation_count',
        'latitude',
        'longitude',
    )
    readonly_fields = (
        'rating',
        'scope_link',
        'citation_count',
    )

    def scope_link(self, obj):
        if obj.scope:
            return format_html(
                '<a href="{}">{}</a>', get_admin_url_for_scope(obj.scope), obj.scope
            )

    actions = [
        'activate',
        'datacite_registration',
        'datacite_update',
        'link_doi_with_collection',
        'offering_referrals_pull',
    ]

    def activate(self, request, queryset):
        valid_states = [models.Offering.States.DRAFT, models.Offering.States.PAUSED]
        valid_offerings = queryset.filter(state__in=valid_states)
        count = valid_offerings.count()

        for offering in valid_offerings:
            offering.activate()
            offering.save()

        message = ungettext(
            'One offering has been activated.',
            '%(count)d offerings have been activated.',
            count,
        )
        message = message % {'count': count}

        self.message_user(request, message)

    activate.short_description = _('Activate offerings')

    def datacite_registration(self, request, queryset):
        queryset = queryset.filter(datacite_doi='')

        for offering in queryset.all():
            pid_utils.create_doi(offering)

        count = queryset.count()
        message = ungettext(
            'One offering has been scheduled for datacite registration.',
            '%(count)d offerings have been scheduled for datacite registration.',
            count,
        )
        message = message % {'count': count}

        self.message_user(request, message)

    datacite_registration.short_description = _('Register in Datacite')

    def datacite_update(self, request, queryset):
        queryset = queryset.exclude(datacite_doi='')

        for offering in queryset.all():
            pid_utils.update_doi(offering)

        count = queryset.count()
        message = ungettext(
            'One offering has been scheduled for updating Datacite registration data.',
            '%(count)d offerings have been scheduled for updating Datacite registration data.',
            count,
        )
        message = message % {'count': count}

        self.message_user(request, message)

    datacite_update.short_description = _('Update data of Datacite registration')

    def link_doi_with_collection(self, request, queryset):
        queryset = queryset.exclude(datacite_doi='')

        for offering in queryset.all():
            serialized_offering = core_utils.serialize_instance(offering)
            pid_tasks.link_doi_with_collection.delay(serialized_offering)

        count = queryset.count()
        message = ungettext(
            'One offering has been scheduled for linking with collection.',
            '%(count)d offerings have been scheduled for linking with collection.',
            count,
        )
        message = message % {'count': count}

        self.message_user(request, message)

    link_doi_with_collection.short_description = _('Link with Datacite Collection')

    def offering_referrals_pull(self, request, queryset):
        queryset.exclude(datacite_doi='')

        for offering in queryset.all():
            serialized_offering = core_utils.serialize_instance(offering)
            pid_tasks.update_referrable.delay(serialized_offering)

        count = queryset.count()

        message = ungettext(
            'Offering has been scheduled for referrals pull.',
            '%(count)d offerings have been scheduled for referrals pull.',
            count,
        )
        message = message % {'count': count}

        self.message_user(request, message)

    offering_referrals_pull.short_description = _('Pull referrals info for offering(s)')


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    fields = ('offering', 'state', 'attributes', 'cost', 'plan', 'resource')
    readonly_fields = fields


class OrderAdmin(
    core_admin.ReadOnlyAdminMixin, core_admin.ExtraActionsMixin, admin.ModelAdmin
):
    list_display = ('uuid', 'project', 'created', 'created_by', 'state', 'total_cost')
    fields = [
        'created_by',
        'approved_by',
        'approved_at',
        'created',
        'project',
        'state',
        'total_cost',
        'modified',
        'pdf_file',
    ]
    readonly_fields = (
        'created',
        'modified',
        'created_by',
        'approved_by',
        'approved_at',
        'project',
        'approved_by',
        'total_cost',
        'pdf_file',
    )

    list_filter = ('state', 'created')
    ordering = ('-created',)
    inlines = [OrderItemInline]

    def get_extra_actions(self):
        return [
            self.create_pdf_for_all,
        ]

    def get_urls(self):
        my_urls = [
            url(
                r'^(.+)/change/pdf_file/$',
                self.admin_site.admin_view(self.pdf_file_view),
            ),
        ]
        return my_urls + super(OrderAdmin, self).get_urls()

    def create_pdf_for_all(self, request):
        tasks.create_pdf_for_all.delay()
        message = _('PDF creation has been scheduled')
        self.message_user(request, message)
        return redirect(reverse('admin:marketplace_order_changelist'))

    def pdf_file_view(self, request, pk=None):
        order = models.Order.objects.get(id=pk)
        file_response = HttpResponse(order.file, content_type='application/pdf')
        filename = order.get_filename()
        file_response[
            'Content-Disposition'
        ] = 'attachment; filename="{filename}"'.format(filename=filename)
        return file_response

    def pdf_file(self, obj):
        if not obj.file:
            return ''

        return format_html('<a href="./pdf_file">download</a>')

    create_pdf_for_all.name = _('Create PDF for all orders')


class ResourceForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ResourceForm, self).__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'offering'):
            # Filter marketplace resource plans by offering
            self.fields['plan'].queryset = self.fields['plan'].queryset.filter(
                offering=self.instance.offering
            )


class SharedOfferingFilter(admin.SimpleListFilter):
    title = _('shared offerings')
    parameter_name = 'shared_offering'

    def lookups(self, request, model_admin):
        options = []

        for offering in models.Offering.objects.filter(shared=True):
            options.append([offering.pk, offering.name])

        return options

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(offering_id=self.value())
        else:
            return queryset


class ResourceAdmin(admin.ModelAdmin):
    form = ResourceForm
    list_display = ('uuid', 'name', 'project', 'state', 'category', 'created')
    list_filter = (
        'state',
        ('project', RelatedOnlyDropdownFilter),
        ('offering', RelatedOnlyDropdownFilter),
        SharedOfferingFilter,
    )
    readonly_fields = (
        'state',
        'scope_link',
        'project_link',
        'offering_link',
        'plan_link',
        'order_item_link',
        'formatted_attributes',
        'formatted_limits',
    )
    fields = readonly_fields + ('plan',)
    date_hierarchy = 'created'
    search_fields = ('name', 'uuid')

    def category(self, obj):
        return obj.offering.category

    def scope_link(self, obj):
        return get_admin_link_for_scope(obj.scope)

    scope_link.short_description = 'Scope'

    def project_link(self, obj):
        return get_admin_link_for_scope(obj.project)

    project_link.short_description = 'Project'

    def offering_link(self, obj):
        return get_admin_link_for_scope(obj.offering)

    offering_link.short_description = 'Offering'

    def plan_link(self, obj):
        return get_admin_link_for_scope(obj.plan)

    plan_link.short_description = 'Plan'

    def order_item_link(self, obj):
        order_item = obj.orderitem_set.filter(
            type=models.OrderItem.Types.CREATE
        ).first()
        if order_item:
            return get_admin_link_for_scope(order_item.order)
        else:
            return ''

    order_item_link.short_description = 'Creation order item'

    def formatted_attributes(self, obj):
        return format_json_field(obj.attributes)

    formatted_attributes.allow_tags = True
    formatted_attributes.short_description = 'Attributes'

    def formatted_limits(self, obj):
        return format_json_field(obj.limits)

    formatted_limits.allow_tags = True
    formatted_limits.short_description = 'Limits'

    class TerminateResources(ExecutorAdminAction):
        executor = executors.TerminateResourceExecutor
        short_description = 'Terminate resources'
        confirmation_description = 'The selected resources and related objects will be deleted. Back up your data.'
        confirmation = True

        def validate(self, resource):
            if resource.state not in (
                models.Resource.States.OK,
                models.Resource.States.ERRED,
            ):
                raise ValidationError(_('Resource has to be in OK or ERRED state.'))

        def get_execute_params(self, request, instance):
            return {'user': request.user}

    terminate_resources = TerminateResources()

    class RestoreLimits(ExecutorAdminAction):
        executor = marketplace_openstack_executors.RestoreTenantLimitsExecutor
        short_description = 'Restore Openstack limits'
        confirmation_description = 'Openstack limits will be restored.'
        confirmation = True

        def validate(self, resource):
            if resource.state != models.Resource.States.OK:
                raise ValidationError(_('Resource has to be in OK state.'))

    restore_limits = RestoreLimits()
    actions = ['terminate_resources', 'restore_limits']


admin.site.register(models.ServiceProvider, ServiceProviderAdmin)
admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.Offering, OfferingAdmin)
admin.site.register(models.Section, SectionAdmin)
admin.site.register(models.Attribute, AttributeAdmin)
admin.site.register(models.Screenshot)
admin.site.register(models.Order, OrderAdmin)
admin.site.register(models.Plan, PlanAdmin)
admin.site.register(models.Resource, ResourceAdmin)
