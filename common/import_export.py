from import_export.admin import ImportMixin, ExportMixin
from django.http import HttpResponse
from django.utils import timezone, encoding
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.db.models import Sum, Count, F

from instructions.models import Instruction
from instructions import model_choices
from organisations.models import OrganisationGeneralPractice, OrganisationClient
from payment.models import InstructionVolumeFee
from import_export.forms import ConfirmImportForm, ImportForm
from import_export.formats.base_formats import CSV
from import_export.admin import DEFAULT_FORMATS
import csv
import io
import zipfile


class CustomImportMixin(ImportMixin):
    import_template_name = 'admin/csv_form.html'


class CustomExportMixin(ExportMixin):

    def get_export_queryset(self, request):
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        list_filter = self.get_list_filter(request)
        search_fields = self.get_search_fields(request)
        if self.get_actions(request):
            list_display = ['action_checkbox'] + list(list_display)

        ChangeList = self.get_changelist(request)
        changelist_kwargs = {
            'request': request,
            'model': self.model,
            'list_display': list_display,
            'list_display_links': list_display_links,
            'list_filter': list_filter,
            'date_hierarchy': self.date_hierarchy,
            'search_fields': search_fields,
            'list_select_related': self.list_select_related,
            'list_per_page': self.list_per_page,
            'list_max_show_all': self.list_max_show_all,
            'list_editable': self.list_editable,
            'model_admin': self,
            'sortable_by': self.sortable_by,
        }
        cl = ChangeList(**changelist_kwargs)

        return cl.get_queryset(request)

    def export_status_report_as_csv(self, request, queryset):
        field_names = ['id', 'medi_ref', 'gp_practice']
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=instruction-status-report:{date}.csv'.format(
            date=timezone.now())
        writer = csv.writer(response)
        writer.writerow(['ID', 'MediRef', 'Surgery', 'Status'])
        for obj in reversed(queryset):
            export_row = [getattr(obj, field) for field in field_names]
            export_row.append(obj.get_status_display())
            row = writer.writerow(export_row)

        return response

    export_status_report_as_csv.short_description = "Export instructions status report"

    def export_client_payment_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=client-payments-report:{date}.csv'.format(
            date=timezone.now())
        writer = csv.writer(response)
        writer.writerow(['Client Id', 'Client Organisation', 'Amount', 'VAT', 'Reference'])
        total_earns_for_each_client_organisation = Instruction.objects.filter(
            status=model_choices.INSTRUCTION_STATUS_COMPLETE,
            client_user__organisation__isnull=False)\
            .values('client_user__organisation')\
            .annotate(
                Count('client_user__organisation'),
                total_earns=Sum(F('gp_earns')+F('medi_earns')),
            ) \
            .order_by('client_user__organisation')

        for total_earn in total_earns_for_each_client_organisation:
            client_organisation = OrganisationClient.objects.get(pk=total_earn['client_user__organisation'])
            try:
                completed_instruction = Instruction.objects.filter(
                    client_user__organisation=client_organisation,
                    status=model_choices.INSTRUCTION_STATUS_COMPLETE
                )
                total_vat = 0
                for instruction in completed_instruction:
                    fee_structure = InstructionVolumeFee.objects.filter(client_org=client_organisation, fee_rate_type=instruction.type_catagory).first()
                    medi_earns_without_vat = instruction.medi_earns * 100 / (100 + fee_structure.vat)
                    total_vat += medi_earns_without_vat * fee_structure.vat / 100
                export_row = [
                    client_organisation.id,
                    client_organisation.trading_name,
                    total_earn['total_earns'] - total_vat,
                    total_vat,
                    ''
                ]
            except ObjectDoesNotExist:
                messages.error(
                    request,
                    "Fee instruction structure of {name} doesn't not exist".format(name=client_organisation.trading_name),
                )
                return redirect(request.path)
            writer.writerow(export_row)
        return response

    export_client_payment_as_csv.short_description = "Export client payment report"

    def export_payment_as_csv(self, request, queryset):
        zipped_file = io.BytesIO()
        date_now = timezone.now()
        with zipfile.ZipFile(zipped_file, 'a', zipfile.ZIP_DEFLATED) as zipped:
            # build payment csv file
            csv_data_payment = io.StringIO()
            writer = csv.writer(csv_data_payment, delimiter=',')
            writer.writerow(['Sort Code', 'Account number', 'GP Surgery', 'Amount', 'VAT', 'Reference'])
            total_earns_for_each_gp_practice = Instruction.objects.filter(status=model_choices.INSTRUCTION_STATUS_COMPLETE)\
                                                .values('gp_practice')\
                                                .annotate(Sum('gp_earns'))\
                                                .order_by('gp_practice')
            for total_earn in total_earns_for_each_gp_practice:
                gp_practice = OrganisationGeneralPractice.objects.get(pk=total_earn['gp_practice'])
                export_row = [
                    gp_practice.payment_bank_sort_code,
                    gp_practice.payment_bank_account_number,
                    gp_practice.name,
                    total_earn['gp_earns__sum'],
                    '',
                    '',
                ]
                writer.writerow(export_row)
            csv_data_payment.seek(0)
            zipped.writestr('payment-report:{date}.csv'.format(date=date_now), csv_data_payment.read())

            # build instruction status report
            instruction_field_names = ['id', 'medi_ref', 'gp_practice']
            csv_data_status = io.StringIO()
            writer = csv.writer(csv_data_status, delimiter=',')
            writer.writerow(['ID', 'MediRef', 'Surgery', 'Status'])
            for obj in reversed(queryset):
                export_row = [getattr(obj, field) for field in instruction_field_names]
                export_row.append(obj.get_status_display())
                writer.writerow(export_row)

            csv_data_status.seek(0)
            zipped.writestr('status-report:{date}.csv'.format(date=date_now), csv_data_status.read())

        zipped_file.seek(0)
        response = HttpResponse(zipped_file, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename=payment-report.zip'
        return response

    export_payment_as_csv.short_description = "Export gp payments report"


class CustomImportExportMixin(CustomImportMixin, CustomExportMixin):

    change_list_template = 'admin/import_export/change_list_import_export.html'


class CustomImportExportModelAdmin(CustomImportExportMixin, admin.ModelAdmin):
    """
        Subclass of ModelAdmin with custom import/export functionality.
    """

    def changelist_view(self, request, extra_context=None):
        if 'action' in request.POST and request.POST['action'] in ['export_payment_as_csv', 'export_client_payment_as_csv']:
            if not request.POST.getlist(admin.ACTION_CHECKBOX_NAME):
                post = request.POST.copy()
                for instruction in Instruction.objects.all():
                    post.update({admin.ACTION_CHECKBOX_NAME: str(instruction.id)})
                request._set_post(post)
        return super().changelist_view(request, extra_context)
