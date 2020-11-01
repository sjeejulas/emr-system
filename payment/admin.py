from django.contrib import admin
from .models import OrganisationFeeRate, InstructionVolumeFee, GpOrganisationFee, WeeklyInvoice
from .model_choices import *
from .forms import OrganisationFeeForm, InstructionVolumeFeeForm
from common.import_export import CustomExportMixin, CustomImportExportModelAdmin
from import_export import resources
from import_export.admin import ExportActionModelAdmin


class OrganisationFeeAdmin(CustomExportMixin, admin.ModelAdmin):
    form = OrganisationFeeForm

    class Media:
        js = ('js/custom_admin/payment_fee_admin.js', )


class GpOrganisationFeeAdmin(admin.ModelAdmin):
    raw_id_fields = ['gp_practice', ]
    list_filter = (
        ('gp_practice', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        'gp_practice', 'organisation_fee__amount_rate_lvl_1', 'organisation_fee__amount_rate_lvl_2'
    )
    list_display = (
        'gp_practice', 'get_amount_rate_lvl_1', 'get_amount_rate_lvl_2'
    )

    def get_amount_rate_lvl_1(self, obj):
        return obj.organisation_fee.amount_rate_lvl_1

    get_amount_rate_lvl_1.admin_order_field = 'organisation_fee'
    get_amount_rate_lvl_1.short_description = 'Earnings for top payment band'

    def get_amount_rate_lvl_2(self, obj):
        return obj.organisation_fee.amount_rate_lvl_2

    get_amount_rate_lvl_2.admin_order_field = 'organisation_fee'
    get_amount_rate_lvl_2.short_description = 'Earnings for lowest payment band'


class InstructionVolumeFeeClientAdmin(admin.ModelAdmin):
    form = InstructionVolumeFeeForm
    raw_id_fields = ('client_org', )
    fields = (
        'client_org', 'max_volume_band_lowest', 'max_volume_band_low', 'max_volume_band_medium', 'max_volume_band_high', 'max_volume_band_top',
        'fee_rate_lowest', 'fee_rate_low', 'fee_rate_medium', 'fee_rate_high', 'fee_rate_top', 'fee_rate_type', 'vat'
    )


class WeeklyInvoiceResource(resources.ModelResource):
    class Meta:
        model = WeeklyInvoice
        fields = ('id', 'start_date', 'end_date', 'number_instructions', 'total_cost', 'paid')

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        columns = []
        for column in dataset.headers:
            columns.append(column.lower())
        dataset.headers = columns


class WeeklyInvoiceAdmin(CustomImportExportModelAdmin, ExportActionModelAdmin):
    resource_class = WeeklyInvoiceResource
    fields = (
        'start_date', 'end_date', 'client_org', 'number_instructions', 'total_cost', 'paid',
        'weekly_invoice_pdf_file', 'status'
    )
    list_display = (
        '__str__', 'status',
    )

    def export_admin_action(self, request, queryset):
        """
        Exports the selected rows using file_format.
        """
        response = super().export_admin_action(request, queryset)

        if request.POST.get('file_format'):
            qs = self.get_export_queryset(request).filter(
                id__in = request.POST.getlist('_selected_action'))
            qs.update(status = INVOICE_PRINTED)

            return response

    actions = [export_admin_action]


admin.site.register(OrganisationFeeRate, OrganisationFeeAdmin)
admin.site.register(InstructionVolumeFee, InstructionVolumeFeeClientAdmin)
admin.site.register(GpOrganisationFee, GpOrganisationFeeAdmin)
admin.site.register(WeeklyInvoice, WeeklyInvoiceAdmin)

