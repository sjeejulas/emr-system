from django.contrib import admin
from . import models
from django.shortcuts import get_object_or_404
from common.import_export import CustomImportExportModelAdmin
from instructions import model_choices
from django.utils import timezone
from datetime import timedelta
from instructions.models import Instruction
from django.db.models import Q
from organisations.models import OrganisationGeneralPractice, OrganisationClient
from instructions.forms import ClientNoteForm, InstructionAdminForm
from import_export import resources
from accounts.models import MedidataUser
from import_export.results import RowResult
from copy import deepcopy
from django.db.transaction import TransactionManagementError
import traceback
import logging
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


class InstructionReminder(admin.TabularInline):
    model = models.InstructionReminder
    readonly_fields = ('note', 'created_date', 'reminder_day')
    extra = 0

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class InstructionClientNote(admin.TabularInline):
    model = models.InstructionClientNote
    readonly_fields = ('created_date', 'created_by')
    form = ClientNoteForm
    extra = 0

    def has_delete_permission(self, request, obj=None):
        if request.user.has_perm('instructions.delete_instruction') or request.user.is_superuser:
            return True
        return False

    def has_add_permission(self, request, obj=None):
        if request.user.has_perm('instructions.add_instruction') or request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.has_perm('instructions.change_instruction') or request.user.is_superuser:
            return True
        return False


class InstructionInternalNote(admin.TabularInline):
    model = models.InstructionInternalNote
    readonly_fields = ('created_date', 'created_by')
    fields = ['note', 'created_date', 'created_by']
    extra = 0

    def has_delete_permission(self, request, obj=None):
        return False


class InstructionConditionsInline(admin.TabularInline):
    model = models.InstructionConditionsOfInterest
    raw_id_fields = ('snomedct',)
    fields = ['snomedct',]

    def get_extra(self, request, obj=None, **kwargs):
        if obj and obj.instructionconditionsofinterest_set.count():
            return 0
        else:
            return 1


class InstructionAdditionQuestionInline(admin.TabularInline):
    model = models.InstructionAdditionQuestion
    fields = ['question']

    def has_delete_permission(self, request, obj=None):
        if request.user.has_perm('instructions.delete_instruction') or request.user.is_superuser:
            return True
        return False

    def has_add_permission(self, request, obj=None):
        if request.user.has_perm('instructions.add_instruction') or request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.has_perm('instructions.change_instruction') or request.user.is_superuser:
            return True
        return False

    def get_extra(self, request, obj=None, **kwargs):
        if obj and obj.instructionconditionsofinterest_set.count():
            return 0
        else:
            return 1


class DaysSinceFilter(admin.SimpleListFilter):
    title = 'Days since created'
    parameter_name = 'created_date'

    MORE_THAN_0 = 5
    MORE_THAN_5 = 10
    MORE_THAN_10 = 15
    MORE_THAN_15 = 0

    def lookups(self, request, model_admin):
        return [
            (self.MORE_THAN_0, '0 to 5 days'),
            (self.MORE_THAN_5, '6 to 10 days'),
            (self.MORE_THAN_10, '11 to 15 days'),
            (self.MORE_THAN_15, 'More than 15 days')
        ]

    def queryset(self, request, queryset):
        days = None
        if self.value():
            days = int(self.value())
        if days == self.MORE_THAN_0:
            date = timezone.now() - timedelta(days=self.MORE_THAN_0)
            return queryset.filter(created__gt=date)
        elif days == self.MORE_THAN_5:
            date_from = timezone.now() - timedelta(days=self.MORE_THAN_5)
            date_to = timezone.now() - timedelta(days=self.MORE_THAN_0)
            return queryset.filter(created__gt=date_from, created__lte=date_to)
        elif days == self.MORE_THAN_10:
            date_from = timezone.now() - timedelta(days=self.MORE_THAN_10)
            date_to = timezone.now() - timedelta(days=self.MORE_THAN_5)
            return queryset.filter(created__gt=date_from, created__lte=date_to)
        elif days == self.MORE_THAN_15:
            date = timezone.now() - timedelta(days=self.MORE_THAN_10)
            return queryset.filter(created__lt=date)
        else:
            return queryset


class CustomStatusFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            (model_choices.INSTRUCTION_STATUS_PAID, 'Paid'),
            (model_choices.INSTRUCTION_STATUS_COMPLETE, 'Completed')
        ]

    def queryset(self, request, queryset):
        selected_status = self.value()

        if selected_status:
            return queryset.filter(status = selected_status)
        return queryset


class ClientOrgFilter(admin.SimpleListFilter):
    title = 'Client'
    parameter_name = 'organisation'

    def lookups(self, request, model_admin):
        organisations = set()
        for client_org in OrganisationClient.objects.all().values_list('id', 'trading_name'):
            organisations.add((client_org[0], client_org[1]))
        return organisations

    def queryset(self, request, queryset):
        organisation_id = self.value()
        if organisation_id:
            return Instruction.objects.filter(client_user__isnull=False, client_user__organisation_id=organisation_id)
        return queryset


class GPOrgFilter(admin.SimpleListFilter):
    title = 'GP Practice'
    parameter_name = 'gp_practice'

    def lookups(self, request, model_admin):
        organisations = set()
        for gp in OrganisationGeneralPractice.objects.filter(live=True).values_list('pk', 'name'):
            organisations.add((gp[0], gp[1]))
        return organisations

    def queryset(self, request, queryset):
        organisation_pk = self.value()
        if organisation_pk:
            return Instruction.objects.filter(gp_practice__practcode=organisation_pk)
        return queryset


class InstructionResource(resources.ModelResource):
    class Meta:
        model = Instruction
        fields = ('id', 'medi_ref', 'status', 'type', 'gp_practice__practcode',
                'gp_practice__billing_address_postalcode', 'client_payment_reference', 'gp_payment_reference')

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        columns = []
        for column in dataset.headers:
            columns.append(column.lower())
        dataset.headers = columns

    def before_import_row(self, row, **kwargs):
        if not row['status'].isdigit():
            instuction_staus_mapping = {
                'new': model_choices.INSTRUCTION_STATUS_NEW,
                'in progress': model_choices.INSTRUCTION_STATUS_PROGRESS,
                'paid': model_choices.INSTRUCTION_STATUS_PAID,
                'completed': model_choices.INSTRUCTION_STATUS_COMPLETE,
                'rejected': model_choices.INSTRUCTION_STATUS_REJECT,
                'finalising': model_choices.INSTRUCTION_STATUS_FINALISE,
            }
            row['status'] = instuction_staus_mapping[str.lower(row['status'])]

    def import_row(self, row, instance_loader, using_transactions=True, dry_run=False, **kwargs):
        row_result = self.get_row_result_class()()
        try:
            self.before_import_row(row, **kwargs)
            instance, new = self.get_or_init_instance(instance_loader, row)
            self.after_import_instance(instance, new, **kwargs)
            if new:
                row_result.import_type = RowResult.IMPORT_TYPE_NEW
            else:
                row_result.import_type = RowResult.IMPORT_TYPE_UPDATE
            row_result.new_record = new
            del instance.medical_with_attachment_report_byte
            del instance.medical_report_byte
            original = deepcopy(instance)
            diff = self.get_diff_class()(self, original, new)
            if self.for_delete(row, instance):
                if new:
                    row_result.import_type = RowResult.IMPORT_TYPE_SKIP
                    diff.compare_with(self, None, dry_run)
                else:
                    row_result.import_type = RowResult.IMPORT_TYPE_DELETE
                    self.delete_instance(instance, using_transactions, dry_run)
                    diff.compare_with(self, None, dry_run)
            else:
                self.import_obj(instance, row, dry_run)
                if self.skip_row(instance, original):
                    row_result.import_type = RowResult.IMPORT_TYPE_SKIP
                else:
                    self.save_instance(instance, using_transactions, dry_run)
                    self.save_m2m(instance, row, using_transactions, dry_run)
                diff.compare_with(self, instance, dry_run)
            row_result.diff = diff.as_html()
            # Add object info to RowResult for LogEntry
            if row_result.import_type != RowResult.IMPORT_TYPE_SKIP:
                row_result.object_id = instance.pk
                row_result.object_repr = force_text(instance)
            self.after_import_row(row, row_result, **kwargs)
        except Exception as e:
            row_result.import_type = RowResult.IMPORT_TYPE_ERROR
            # There is no point logging a transaction error for each row
            # when only the original error is likely to be relevant
            if not isinstance(e, TransactionManagementError):
                logging.exception(e)
            tb_info = traceback.format_exc()
            row_result.errors.append(self.get_error_result_class()(e, tb_info, row))
        return row_result


class InstructionAdmin(CustomImportExportModelAdmin):
    change_status = False
    show_full_result_count = False
    form = InstructionAdminForm
    list_display = ('gp_practice', 'client', 'status', 'created', 'type', 'days_since_created')
    list_filter = (
        'type', DaysSinceFilter, ClientOrgFilter, GPOrgFilter, CustomStatusFilter
    )
    resource_class = InstructionResource
    raw_id_fields = ('gp_practice', )
    readonly_fields = ('medi_ref', 'get_client_org_name',)
    actions = ['export_status_report_as_csv', 'export_payment_as_csv', 'export_client_payment_as_csv']
    search_fields = [
        'medi_ref', 'your_ref', 'patient_information__patient_first_name', 'patient_information__patient_last_name'
    ]

    fieldsets = (
        ('Instruction Information', {
            'fields': (
                'status', 'get_client_org_name', 'client_user', 'gp_user', 'patient_information', 'type', 'gp_practice', 'date_range_from', 'date_range_to', 'your_ref', 'medi_ref',
                'gp_title_from_client', 'gp_initial_from_client', 'gp_last_name_from_client', 'deactivated', 'patient_acceptance'
            )
        }),
        ('Rejected Information', {
            'fields': (
                'rejected_timestamp', 'rejected_by', 'rejected_note', 'rejected_reason'
            )
        }),
        ('Final report Information', {
            'fields': (
                'completed_signed_off_timestamp', 'final_report_date',
            )
        }),
        ('Consents Information', {
            'fields': (
                'consent_form', 'sars_consent', 'mdx_consent'
            )
        }),
        ('Payment Information', {
            'fields': (
                'gp_earns', 'medi_earns', 'client_payment_reference', 'gp_payment_reference', 'invoice_in_week',
                'invoice_pdf_file'
            )
        })
    )

    inlines = [
        InstructionReminder,
        InstructionClientNote,
        InstructionInternalNote,
        InstructionConditionsInline,
        InstructionAdditionQuestionInline
    ]

    def get_inline_instances(self, request, obj=None):
        self.inlines = []
        self.inlines.append(InstructionReminder)
        self.inlines.append(InstructionClientNote)
        self.inlines.append(InstructionConditionsInline)
        if request.user.has_perm('instructions.view_instructionadditionquestion') or request.user.is_superuser:
            self.inlines.append(InstructionAdditionQuestionInline)
        return super(InstructionAdmin, self).get_inline_instances(request, obj)

    def get_readonly_fields(self, request, obj=None):
        user = request.user
        if hasattr(user, 'userprofilebase') and hasattr(user.userprofilebase, 'medidatauser') and\
                request.user.userprofilebase.medidatauser.role == MedidataUser.MEDI_ADMIN:
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super(InstructionAdmin, self) \
            .get_search_results(request, queryset, search_term)
        gp_organisations = [gp_org.pk for gp_org in OrganisationGeneralPractice.objects.filter(name__icontains=search_term)]
        queryset |= queryset.filter(
            Q(gp_practice__pk__in=gp_organisations) |
            Q(client_user__organisation__trading_name__icontains=search_term)
        )
        return queryset, use_distinct

    def client(self, instance):
        client_organisation = ''
        if instance.client_user:
            client_organisation = instance.client_user.organisation.__str__()
        return client_organisation

    def days_since_created(self, instance):
        return (timezone.now().date() - instance.created.date()).days

    def save_model(self, request, obj, form, change):
        change_status = False
        if 'status' in form.changed_data:
            self.change_status = True
        super(InstructionAdmin, self).save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super(InstructionAdmin, self).save_related(request, form, formsets, change)
        if self.change_status:
            pk = form.instance.id
            instruction = get_object_or_404(models.Instruction, pk=pk)
            if instruction.status == model_choices.INSTRUCTION_STATUS_REJECT:
                if instruction.client_user:
                    instruction.send_reject_email([instruction.client_user.user.email, instruction.gp_user.user.email])
                else:
                    instruction.send_reject_email([instruction.gp_user.user.email])

    def save_formset(self, request, form, formset, change):
        if formset.model == models.InstructionInternalNote or formset.model == models.InstructionClientNote:
            instances = formset.save(commit=False)
            for instance in instances:
                instance.created_by = request.user
                instance.save()
            formset.save_m2m()
        super(InstructionAdmin, self).save_formset(request, form, formset, change)


admin.site.register(models.Instruction, InstructionAdmin)
admin.site.register(models.InstructionAdditionQuestion)
admin.site.register(models.Setting)
admin.site.register(models.ClientNote)
admin.site.register(models.InstructionPatient)
