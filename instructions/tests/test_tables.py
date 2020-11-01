from django.test import RequestFactory, TestCase
from django.utils import timezone
from django.shortcuts import render
from django_tables2 import RequestConfig, Column

from model_mommy import mommy

from organisations.models import OrganisationClient, OrganisationGeneralPractice
from accounts.models import ClientUser, GeneralPracticeUser, User, GENERAL_PRACTICE_USER
from instructions.models import (
    Instruction, InstructionPatient
)
from instructions.model_choices import INSTRUCTION_STATUS_PROGRESS, AMRA_TYPE
from instructions.tables import InstructionTable
from django.urls import resolve

from instructions.views import get_table_fee_sensitive
from payment.model_choices import FEE_UNDERWRITE_TYPE
from payment.models import InstructionVolumeFee, GpOrganisationFee, OrganisationFeeRate


class TestRenderTables(TestCase):
    def setUp(self):
        self.client_name = 'Test Trading Name Client Organisation'
        self.patient_first_name = 'aaa'
        self.patient_last_name = 'bbb'
        self.gp_user_name = 'gpuser'
        self.gp_earns = '500.00'
        self.vat = 20
        self.fee_rate = 100

        self.request = RequestFactory()
        self.date_instructions = timezone.now()
        self.client_organisation = mommy.make(OrganisationClient, trading_name=self.client_name)
        self.client_user = mommy.make(
            ClientUser, organisation=self.client_organisation,
            role=ClientUser.CLIENT_MANAGER,
        )
        self.instruction_patient = mommy.make(
            InstructionPatient,
            patient_title='MR',
            patient_first_name=self.patient_first_name,
            patient_last_name=self.patient_last_name
        )
        self.gp_practice = mommy.make( OrganisationGeneralPractice, name='Test GP Practice', practcode='TEST0001' )
        self.user = mommy.make(User, username=self.gp_user_name, first_name=self.gp_user_name )

        self.gp_user = mommy.make(
            GeneralPracticeUser,
            organisation=self.gp_practice,
            user=self.user,
            role=0,
            title='DR'
        )
        
        self.instruction = mommy.make(
            Instruction, gp_practice=self.gp_practice, client_user=self.client_user, type=AMRA_TYPE, type_catagory=FEE_UNDERWRITE_TYPE, patient_information=self.instruction_patient,
            gp_user=self.gp_user, gp_earns=self.gp_earns, medi_earns=100, status=INSTRUCTION_STATUS_PROGRESS
        )

        self.user_test = mommy.make(User, username='gpTest', first_name='gpTest', is_active=True, type=GENERAL_PRACTICE_USER)
        self.request_user = mommy.make(
            GeneralPracticeUser,
            organisation=self.gp_practice,
            user=self.user_test,
            role=0
        )

        self.ins_volume_fee = mommy.make(
            InstructionVolumeFee,
            client_org = self.client_organisation,
            max_volume_band_lowest = 1, fee_rate_lowest = self.fee_rate,
            max_volume_band_low = 2, fee_rate_low = 90,
            max_volume_band_medium = 3, fee_rate_medium = 80,
            max_volume_band_high = 4, fee_rate_high = 70,
            max_volume_band_top = 5, fee_rate_top = 60,
            fee_rate_type = FEE_UNDERWRITE_TYPE,
            vat = self.vat
        )

        self.fee_rate_gp = 70
        self.brand_gp = mommy.make(
            OrganisationFeeRate,
            name='Surgery Fee',
            amount_rate_lvl_1= self.fee_rate_gp,
            amount_rate_lvl_2=60,
            amount_rate_lvl_3=50,
            amount_rate_lvl_4=40,
            default=True
        )

        self.select_brand = mommy.make(
            GpOrganisationFee,
            gp_practice = self.gp_practice,
            organisation_fee = self.brand_gp
        )

    def test_render_gp(self):
        request = self.request.get('/instruction/view-pipeline')
        request.user = self.user_test
        request.resolver_match = resolve('/instruction/view-pipeline/')

        instruction_query_set = Instruction.objects.all()
        table_all = InstructionTable(instruction_query_set, extra_columns=[('cost', Column(empty_values=(), verbose_name='Income £'))])
        RequestConfig(request, paginate={'per_page': 5}).configure(table_all)

        self.request.GET = dict()
        table_fee = get_table_fee_sensitive(self.request, self.gp_practice.practcode)
        response = render(request, 'instructions/pipeline_views_instruction.html',  {'table_all': table_all, 'table_fee': table_fee})
        
        result_html_str = str(response.content)
        self.fee_rate_gp = format(self.fee_rate_gp, '.2f')
        expected_cost_value = float(self.gp_earns) + self.fee_rate + (self.fee_rate * (self.vat / 100))
        expected_client_name = '<td class="client_user">' + self.client_name + '</td>'
        expected_instructions_type = '<td class="type">' + AMRA_TYPE + '</td>'
        expected_patient_name = '<td class="patient_information">Mr. ' + self.patient_first_name + ' ' + self.patient_last_name + ' <br><b>NHS: </b></td>'
        expected_gp_allocated = '<td class="gp_user">Dr. ' + self.gp_user_name + ' </td>'
        expected_cost = '<td class="cost">' + str(self.fee_rate_gp) + '</td>'
        expected_created = '<td class="created">' + str( self.date_instructions.strftime('%-d %b %Y')) + '</td>'
        expected_status = '<td class="status"><a href=/medicalreport/'+ str(self.instruction.id) +'/edit/><h5><span class="status badge badge-warning">'\
                            + 'In Progress' + '</span></h5></a></td>'

        self.assertInHTML(expected_client_name, result_html_str)
        self.assertInHTML(expected_instructions_type, result_html_str)
        self.assertInHTML(expected_patient_name, result_html_str)
        self.assertInHTML(expected_gp_allocated, result_html_str)
        self.assertInHTML(expected_cost, result_html_str)
        self.assertInHTML(expected_created, result_html_str)
        self.assertInHTML(expected_status, result_html_str)
