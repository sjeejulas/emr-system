import django_tables2 as tables
from .models import User
import django_tables2 as tables
from accounts import models
from instructions.models import Instruction
from django.utils.html import format_html
from django.urls import reverse
from permissions.templatetags.get_permissions import view_complete_report
from django.template.defaultfilters import date
from payment.models import WeeklyInvoice
from organisations.models import OrganisationMedidata
from django.utils import timezone
from datetime import timedelta
from payment.functions import PaymentInvoice 
from django.conf import settings
import uuid


class UserTable(tables.Table):
    chkbox = tables.CheckBoxColumn(attrs={'id': 'check_all', "th__input": {"onclick": "toggleUserTableHeadChk(this)"}}, accessor="email")
    role = tables.Column(verbose_name='Role', accessor="userprofilebase")
    organisation = tables.Column(verbose_name='Organisation', accessor="userprofilebase")
    email = tables.Column(verbose_name='Email', accessor='email')
    name = tables.Column(verbose_name='Name', accessor='userprofilebase')

    class Meta:
        attrs = {
            'class': 'table table-striped table-bordered table-hover',
            'id': 'usersTable'
        }
        model = User
        fields = ('chkbox', 'email', 'name', 'organisation', 'role')
        template_name = 'django_tables2/semantic.html'

    def render_name(self, value):
        return "%s %s"%(value.get_title_display(), value.user.get_full_name())

    def render_role(self, value):
        return value.user.get_short_my_role()

    def render_organisation(self, value):
        if hasattr(value, 'generalpracticeuser'):
            return value.generalpracticeuser.organisation.__str__()
        elif hasattr(value, 'medidatauser'):
            return value.medidatauser.organisation.__str__()
        else:
            return value.clientuser.organisation.__str__()


class AccountTable(tables.Table):
    patient_information = tables.Column()
    client_ref = tables.Column(empty_values=(), default='-')
    instruction_information = tables.Column(empty_values=(), default='-')
    PDF_copy_of_invoice = tables.Column(empty_values=(), default='-')
    complete_date = tables.DateTimeColumn(format='D j M Y')
    user = None

    class Meta:
        attrs = {
            'class': 'table table-striped table-bordered table-hover',
            'id': 'instructionsTable'
        }
        model = Instruction
        fields = (
            'status', 'client_ref', 'medi_ref', 'patient_information', 'cost', 
            'type', 'complete_date', 'instruction_information',
            'PDF_copy_of_invoice'
        )
        template_name = 'django_tables2/semantic.html'
        row_attrs = {
            'data-id': lambda record: record.pk
        }

    def render_type(self, record):
        type = record.type
        type_catagory = record.type_catagory
        if type_catagory:
            if type_catagory == 1:
                type_detail = 'Claims'
            elif type_catagory == 2:
                type_detail = 'Underwriting'
            else:
                type_detail = 'Sars'
            return format_html(
                '<strong>{}</strong><br> <font size="-1">( {} )</font>', type, type_detail
            )
        else:
            return format_html(
                '<strong>{}</strong>', type
            )

    def render_status(self, value, record):
        STATUS_DICT = {
            'New': 'badge-primary',
            'In Progress': 'badge-warning',
            'Paid': 'badge-info',
            'Completed': 'badge-success',
            'Rejected': 'badge-danger',
            'Finalising': 'badge-secondary',
            'Rerun': 'badge-dark'
        }
        return format_html('<h5><span class="status badge {}">{}</span></h5></a>', STATUS_DICT[value], value)

    def render_client_ref(self, record):
        client_ref = record.your_ref
        if not client_ref:
            client_ref = "—"
        return format_html(client_ref)

    def render_patient_information(self, value):
        return format_html(
            '{} {} {} <br><b>NHS: </b>{}', value.get_patient_title_display(), value.patient_first_name, value.patient_last_name, value.patient_nhs_number
        )

    def render_cost(self, record):
        return record.gp_earns + record.medi_earns

    def render_complete_date(self, record):
        return record.completed_signed_off_timestamp

    def render_instruction_information(self, record):
        gp_practice = record.gp_practice
        client_user = record.client_user
        patient = record.patient_information
        snomed_detail = ''
        for snomed in record.get_inner_selected_snomed_concepts():
            if snomed_detail == '':
                snomed_detail = snomed
            else:
                snomed_detail = snomed_detail + ', ' + snomed
        
        if record.fee_calculation_start_date and record.completed_signed_off_timestamp:
            calculate_date = record.completed_signed_off_timestamp - record.fee_calculation_start_date
            calculate_date = " ".join([str(calculate_date.days), "days"])
        else:
            calculate_date = 'None'

        return format_html(
            "<a href='#infoModal'>"
            "<span class='btn btn-primary btn-block btn-sm infoDetailButton'"
            "data-patient_name='{}'"
            "data-patient_dob='{}'"
            "data-patient_address='{}'"
            "data-patient_nhs='{}'"
            "data-patient_client_ref='{}'"
            "data-patient_medi_ref='{}'"
            "data-detail_request='{}'"
            "data-detail_start_date='{}'"
            "data-detail_complete_date='{}'"
            "data-result_date='{}'"
            "><i class='fas fa-search'></i>&nbsp;&nbsp;View</span>"
            "</a>",
            patient.get_full_name(),
            date(patient.patient_dob, "d/m/Y"),
            ' '.join([
                    patient.patient_address_number,
                    patient.patient_address_line1,
                    patient.patient_address_line2,
                    patient.patient_address_line3,
                    patient.patient_city,
                    patient.patient_county
                ]),
            patient.patient_nhs_number if patient.patient_nhs_number else '-',
            record.your_ref if record.your_ref else '-',
            record.medi_ref if record.medi_ref else '-',
            snomed_detail if not snomed_detail == '' else 'None',
            date(record.fee_calculation_start_date, "d/m/Y") if record.fee_calculation_start_date else 'None',
            date(record.completed_signed_off_timestamp, "d/m/Y") if record.completed_signed_off_timestamp else 'None',
            calculate_date
        )

    def render_PDF_copy_of_invoice(self, record):
        if not record.invoice_pdf_file:
            medi_user = OrganisationMedidata.objects.first()
            now = timezone.now()
            date_detail = {
                'date_invoice': now,
                'dute_date': now + timedelta(days=7)
            }
            client_detail = record.client_user.organisation
            params = {
                'client_detail': client_detail,
                'medi_detail': medi_user,
                'date_detail': date_detail,
                'record': [record, ]
            }

            uuid_hex = uuid.uuid4().hex
            record.invoice_pdf_file.save('invoice_%s.pdf'%uuid_hex, PaymentInvoice.get_invoice_pdf_file(params))
        
        path = settings.MEDIA_URL + str(record.invoice_pdf_file)
        return format_html(
            '<a href="{}" target="_blank">'
            '<button type="button" class="btn btn-success btn-block btn-sm">'
            '<i class="fas fa-search"></i>&nbsp;&nbsp;Click to preview'
            '</button>'
            '</a>',
            path
        )


class PaymentLogTable(tables.Table):
    invoice_attachment = tables.Column(empty_values=(), default='-')
    status = tables.Column(empty_values=(), default='-', attrs={
        'td': {
            'class': 'status_paid'
        }
    })
 
    class Meta:
        attrs = {
            'class': 'table table-bordered text-center',
            'id': 'WeeklyInvoiceTable'
        }
        model = WeeklyInvoice
        fields = (
            'start_date', 'end_date', 'number_instructions', 'total_cost', 'status',
            'invoice_attachment'
        )
        template_name = 'django_tables2/semantic.html'
        row_attrs = {
            'class': 'block_unpaid'
        }

    def render_status(self, record):
        status = "Paid" if record.paid else "Unpaid"
        return format_html("<strong>{}</strong>", status)

    def render_invoice_attachment(self, record):
        path = settings.MEDIA_URL + str(record.weekly_invoice_pdf_file)
        return format_html(
            '<a href="{}" target="_blank">'
            '<button type="button" class="btn btn-secondary btn-block btn-sm">'
            '<i class="fas fa-search"></i>&nbsp;&nbsp;Click to preview'
            '</button>'
            '</a>',
            path
        )