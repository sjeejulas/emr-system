import django_tables2 as tables
from accounts import models
from .models import Instruction
from django.utils.html import format_html
from django.urls import reverse
from permissions.templatetags.get_permissions import view_complete_report
from payment.functions import calculate_gp_earn, calculate_medi_earn


class InstructionTable(tables.Table):
    patient_information = tables.Column()
    client_ref = tables.Column(empty_values=(), default='-')
    created = tables.DateTimeColumn(format='j M Y')
    status = tables.Column()
    user = None

    class Meta:
        attrs = {
            'class': 'table table-striped table-bordered table-hover',
            'id': 'instructionsTable'
        }
        model = Instruction
        fields = (
            'client_ref', 'client_user', 'gp_practice', 'type', 'patient_information', 'medi_ref', 'your_ref',
            'gp_user', 'cost', 'created', 'completed_signed_off_timestamp', 'status', 'fee_note'
        )
        template_name = 'django_tables2/semantic.html'
        row_attrs = {
            'data-id': lambda record: record.pk
        }

    def before_render(self, request):
        if request.user.type == models.CLIENT_USER:
            self.columns.hide('client_user')
        elif request.user.type == models.GENERAL_PRACTICE_USER:
            self.columns.hide('gp_practice')
            self.columns.hide('client_ref')

        if request.resolver_match.url_name == 'view_pipeline':
            self.columns.hide('medi_ref')
            self.columns.hide('your_ref')
            self.columns.hide('completed_signed_off_timestamp')
            self.columns.hide('fee_note')
        elif request.resolver_match.url_name == 'view_invoice_payment_pipeline':
            self.columns.hide('gp_user')
            self.columns.hide('created')
            self.columns.hide('client_ref')

        self.current_url = request.resolver_match.url_name
        self.user = request.user

    def render_gp_user(self, record):
        gp_users_string = ''
        selected_string = ''

        if self.current_url == 'view_pipeline' and \
           self.user.has_perm('instructions.allocate_gp'):
            gp_users = models.GeneralPracticeUser.objects.all()

            for index, gp_user in enumerate(gp_users):
                if not gp_user.user.has_perm('instructions.process_sars') and \
                   not gp_user.user.has_perm('instructions.process_amra'):
                   continue
                if gp_user.user == record.gp_user.user:
                    selected_string = 'selected'
                else:
                    selected_string = ''

                gp_users_string += "<option value='{}' {} data-gp_id={}>{}</option>".format(
                    str(index),
                    selected_string,
                    gp_user.pk,
                    str(gp_user.user)
                )
        if gp_users_string:
            return format_html(
                "<select class='form-control btn sel_gp_users' name='gp_users'>" + \
                gp_users_string + \
                "</select>"
            )

        return format_html(str(record.gp_user))

    def render_client_ref(self, record):
        client_ref = record.your_ref
        if not client_ref:
            client_ref = "_"
        return format_html(client_ref)

    def render_client_user(self, value):
        user = value.user
        trading_name = ""
        if hasattr(user, 'userprofilebase') and hasattr(user.userprofilebase, 'clientuser') and\
            user.userprofilebase.organisation:
            trading_name = user.userprofilebase.clientuser.organisation.trading_name
        return format_html(trading_name)

    def render_patient_information(self, value):
        return format_html(
            '{} {} {} <br><b>NHS: </b>{}', value.get_patient_title_display(), value.patient_first_name, value.patient_last_name, value.patient_nhs_number
        )

    def render_cost(self, record):
        if self.user.type == models.CLIENT_USER or self.user.type == models.MEDIDATA_USER:
            if record.gp_earns == 0 and record.medi_earns == 0:
                client_cost = calculate_medi_earn(record) + calculate_gp_earn(record)
                return format(client_cost, '.2f')
            return record.gp_earns + record.medi_earns
        elif self.user.type == models.GENERAL_PRACTICE_USER:
            gp_earns = record.gp_earns
            if record.get_type() == 'AMRA':
                gp_earns = calculate_gp_earn(record)
            return gp_earns

    def render_status(self, value, record):
        STATUS_DICT = {
            'New': 'badge-primary',
            'In Progress': 'badge-warning',
            'Paid': 'badge-info',
            'Completed': 'badge-success',
            'Rejected': 'badge-danger',
            'Finalising': 'badge-secondary',
            'Rerun': 'badge-dark',
            'Redacting': 'badge-light',
        }
        url = 'instructions:review_instruction'
        view_report = view_complete_report(self.user.id, record.pk)
        if value == 'Completed':
            if self.user.type != models.GENERAL_PRACTICE_USER:
                url = 'medicalreport:final_report'
            elif view_report:
                url = 'medicalreport:final_report'
            else:
                return format_html('<a><h5><span class="status badge {}">{}</span></h5></a>', STATUS_DICT[value], value)
        elif value == 'Rejected':
            url = 'instructions:view_reject'
        elif value == 'Rerun':
            url = 'instructions:view_fail'
        elif value == 'In Progress' and self.user.type == models.GENERAL_PRACTICE_USER and not record.saved:
            url = 'medicalreport:edit_report'
        elif value == 'In Progress' and self.user.type == models.GENERAL_PRACTICE_USER and record.saved:
            url = 'instructions:consent_contact'
            return format_html('<a href='+reverse(url, args=[record.pk, record.patient_information.patient_emis_number])+'><h5><span class="status badge {}">{}</span></h5></a>', STATUS_DICT[value], value)
        return format_html('<a href='+reverse(url, args=[record.pk])+'><h5><span class="status badge {}">{}</span></h5></a>', STATUS_DICT[value], value)

    def render_fee_note(self, record):
        gp_practice = record.gp_practice
        client_user = record.client_user
        trading_name = client_user.organisation.trading_name if client_user else '-'
        return format_html(
            "<a href='#feeNoteModal'>"
            "<h5><span class='feeNote badge noteDetailButton'"
            "data-surgeryName='{}'"
            "data-surgeryAddress='{}'"
            "data-clientName='{}'"
            "data-clientRef='{}'"
            "data-patientName='{}'"
            "data-mediRef='{}'"
            "data-receivedDate='{}'"
            "data-completedDate='{}'"
            "data-gpFee='{}'>"
            "View</span></h5>"
            "</a>",
            gp_practice.name,
            ' '.join([
                    gp_practice.billing_address_street,
                    gp_practice.billing_address_line_2,
                    gp_practice.billing_address_line_3,
                    gp_practice.billing_address_city,
                    gp_practice.billing_address_state,
                    gp_practice.billing_address_postalcode,
                ]),
            trading_name,
            record.your_ref if record.your_ref else '-',
            record.patient_information,
            record.medi_ref,
            record.created.strftime("%d/%m/%Y"),
            record.completed_signed_off_timestamp.strftime("%d/%m/%Y") if record.completed_signed_off_timestamp else '-',
            record.gp_earns,
        )


class FeeInstructionTable(tables.Table):
    patient_information = tables.Column()
    client_ref = tables.Column(empty_values=(), default='-')
    created = tables.DateTimeColumn(format='j M Y')
    status = tables.Column()
    user = None

    class Meta:
        attrs = {
            'class': 'table table-striped table-bordered table-hover',
            'id': 'feeInstructionsTable'
        }
        model = Instruction
        fields = (
            'client_ref', 'client_user', 'gp_practice', 'type', 'patient_information', 'medi_ref', 'your_ref',
            'gp_user', 'cost', 'created', 'completed_signed_off_timestamp', 'status', 'fee_note'
        )
        template_name = 'django_tables2/semantic.html'
        row_attrs = {
            'data-id': lambda record: record.pk
        }

    def before_render(self, request):
        if request.user.type == models.CLIENT_USER:
            self.columns.hide('client_user')
        elif request.user.type == models.GENERAL_PRACTICE_USER:
            self.columns.hide('gp_practice')
            self.columns.hide('client_ref')

        if request.resolver_match.url_name == 'view_pipeline':
            self.columns.hide('medi_ref')
            self.columns.hide('your_ref')
            self.columns.hide('completed_signed_off_timestamp')
            self.columns.hide('fee_note')
        elif request.resolver_match.url_name == 'view_invoice_payment_pipeline':
            self.columns.hide('gp_user')
            self.columns.hide('created')
            self.columns.hide('client_ref')

        self.user = request.user

    def render_client_ref(self, record):
        client_ref = record.your_ref
        if not client_ref:
            client_ref = "_"
        return format_html(client_ref)

    def render_client_user(self, value):
        user = value.user
        trading_name = ""
        if hasattr(user, 'userprofilebase') and hasattr(user.userprofilebase, 'clientuser') and\
            user.userprofilebase.organisation:
            trading_name = user.userprofilebase.clientuser.organisation.trading_name
        return format_html(trading_name)

    def render_patient_information(self, value):
        return format_html(
            '{} {} {} <br><b>NHS: </b>{}', value.get_patient_title_display(), value.patient_first_name, value.patient_last_name, value.patient_nhs_number
        )

    def render_cost(self, record):
        if self.user.type == models.CLIENT_USER or self.user.type == models.MEDIDATA_USER:
            return record.gp_earns + record.medi_earns
        elif self.user.type == models.GENERAL_PRACTICE_USER:
            return record.gp_earns

    def render_status(self, value, record):
        STATUS_DICT = {
            'New': 'badge-primary',
            'In Progress': 'badge-warning',
            'Paid': 'badge-info',
            'Completed': 'badge-success',
            'Rejected': 'badge-danger',
            'Finalising': 'badge-secondary',
            'Rerun': 'badge-dark',
            'Redacting': 'badge-light',
        }
        url = 'instructions:review_instruction'
        view_report = view_complete_report(self.user.id, record.pk)
        if value == 'Completed':
            if self.user.type != models.GENERAL_PRACTICE_USER:
                url = 'medicalreport:final_report'
            elif view_report:
                url = 'medicalreport:final_report'
            else:
                return format_html('<a><h5><span class="status badge {}">{}</span></h5></a>', STATUS_DICT[value], value)
        elif value == 'Rejected':
            url = 'instructions:view_reject'
        elif value == 'Rerun':
            url = 'instructions:view_fail'
        elif value == 'In Progress' and self.user.type == models.GENERAL_PRACTICE_USER and not record.saved:
            url = 'medicalreport:edit_report'
        elif value == 'In Progress' and self.user.type == models.GENERAL_PRACTICE_USER and record.saved:
            url = 'instructions:consent_contact'
            return format_html('<a href='+reverse(url, args=[record.pk, record.patient_information.patient_emis_number])+'><h5><span class="status badge {}">{}</span></h5></a>', STATUS_DICT[value], value)
        return format_html('<a href='+reverse(url, args=[record.pk])+'><h5><span class="status badge {}">{}</span></h5></a>', STATUS_DICT[value], value)