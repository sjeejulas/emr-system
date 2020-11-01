from django.contrib import admin
from common.import_export import CustomImportExportModelAdmin
from import_export import resources
from django import forms
from .models import OrganisationMedidata, OrganisationGeneralPractice, OrganisationClient


class OrganisationGeneralPracticeResource(resources.ModelResource):
    class Meta:
        model = OrganisationGeneralPractice
        import_id_fields = ('practcode',)
        skip_unchanged = True

    def skip_row(self, instance, original):
        if OrganisationGeneralPractice.objects.filter(practcode=instance.practcode).exists():
            return True
        return super().skip_row(instance, original)


class OrganisationGeneralPracticeForm(forms.ModelForm):
    class Meta:
        model = OrganisationGeneralPractice
        fields = '__all__'


class OrganisationGeneralPracticeAdmin(CustomImportExportModelAdmin):
    skip_admin_log = True
    search_fields = ['name', 'practcode']
    resource_class = OrganisationGeneralPracticeResource
    readonly_fields = ('_operating_system_salt_and_encrypted_password',)
    form = OrganisationGeneralPracticeForm
    list_display = ('name', 'practcode')
    fieldsets = (
        ('Organisation Information', {
            'fields': ('name', 'practcode',)
        }),
        ('Address Information', {
            'fields': (
                'region', 'comm_area', 'billing_address_street', 'billing_address_line_2', 'billing_address_line_3',
                'billing_address_city', 'billing_address_state', 'billing_address_postalcode'
            )
        }),
        ('Contact Information', {
            'fields': ('phone_office', 'phone_alternate', 'phone_onboarding_setup', 'organisation_email', 'fax', 'website')
        }),
        ('System Information', {
            'fields': (
                'gp_operating_system', 'operating_system_socket_endpoint', 'operating_system_organisation_code', 'operating_system_username',
                '_operating_system_salt_and_encrypted_password', 'operating_system_auth_token'
            )
        }),
        ('Payment Information', {
            'fields': (
                'payment_timing', 'payment_bank_holder_name', 'payment_bank_sort_code', 'payment_bank_account_number',
                'payment_preference',
            )
        }),
        ('Addition Information', {
            'fields': (
                'practicemanagername_c', 'practicemanager_job_title', 'patientlistsize_c', 'sitenumber_c', 'employees',
                'ownership', 'ccg_health_board_c'
            )
        }),
        ('Organisation Status', {
            'fields': (
                'accept_policy', 'live', 'live_timechecked'
            )
        })
    )

    def get_queryset(self, request):
        qs = super(OrganisationGeneralPracticeAdmin, self).get_queryset(request)
        qs = qs.order_by('name')
        return qs


class OrganisationClientForm(forms.ModelForm):
    class Meta:
        model = OrganisationClient
        fields = '__all__'


class OrganisationClientAdmin(admin.ModelAdmin):
    form = OrganisationClientForm
    fieldsets = (
        ('Organisation Information', {'fields': ('trading_name', 'legal_name', 'address', 'type')}),
        ('Addition Information', {
            'classes': ('hidden', 'additionInfo'),
            'fields': ('contact_name', 'contact_telephone', 'contact_email', 'generic_telephone', 'generic_email',
                       'fax_number', 'companies_house_number', 'vat_number')}),
        ('Insurance: Addition Information', {
            'classes': ('hidden', 'Insurance'),
            'fields': ('division', 'fca_number')}),
    )

    class Media:
        js = ('js/custom_admin/organisation_admin.js', )


class OrganisationMedidataAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        query_set = super(OrganisationMedidataAdmin, self).get_queryset(request)
        client_organisation_query = OrganisationClient.objects.all()
        filtered_queryset = query_set.exclude(id__in=client_organisation_query)
        return filtered_queryset


admin.site.register(OrganisationClient, OrganisationClientAdmin)
admin.site.register(OrganisationGeneralPractice, OrganisationGeneralPracticeAdmin)
admin.site.register(OrganisationMedidata, OrganisationMedidataAdmin)
