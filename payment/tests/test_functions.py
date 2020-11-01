from ..functions import calculate_instruction_fee
from accounts.models import ClientUser, GeneralPracticeUser
from organisations.models import OrganisationClient, OrganisationGeneralPractice
from instructions import model_choices
from instructions.models import Instruction
from payment.models import InstructionVolumeFee, OrganisationFeeRate, GpOrganisationFee
from payment.model_choices import *
from model_mommy import mommy
from django.test import TestCase
from django.utils import timezone


class CalculateInstructionFeeBaseTest(TestCase):

    def setUp(self):
        self.client_organisation = mommy.make(
            OrganisationClient, trading_name='Test Trading Name Client Organisation'
        )
        self.client_user = mommy.make(
            ClientUser, organisation=self.client_organisation,
            role=ClientUser.CLIENT_MANAGER,
        )
        self.gp_practice = mommy.make(
            OrganisationGeneralPractice,
            name='Test Name GP Organisation',
            payment_bank_sort_code='12-34-56',
            payment_bank_account_number='12345678'
        )
        self.amra_instruction = mommy.make(
            Instruction, type=model_choices.AMRA_TYPE,
            gp_practice=self.gp_practice,
            client_user=self.client_user,
            created=timezone.now(),
            completed_signed_off_timestamp=timezone.now(),
            fee_calculation_start_date=timezone.now(),
            type_catagory=FEE_CLAIMS_TYPE
        )
        self.sars_instruction = mommy.make(
            Instruction, type=model_choices.SARS_TYPE,
            gp_practice=self.gp_practice,
            client_user=self.client_user,
            created=timezone.now(),
            completed_signed_off_timestamp=timezone.now(),
            fee_calculation_start_date=timezone.now(),
            type_catagory=FEE_SARS_TYPE
        )

        self.organisation_fee = mommy.make(
            OrganisationFeeRate,
            max_day_lvl_1=3,
            max_day_lvl_2=6,
            max_day_lvl_3=8,
            max_day_lvl_4=10,
            amount_rate_lvl_1=70,
            amount_rate_lvl_2=50,
            amount_rate_lvl_3=30,
            amount_rate_lvl_4=20
        )

        self.gp_fee_relation = mommy.make(
            GpOrganisationFee,
            gp_practice=self.gp_practice,
            organisation_fee=self.organisation_fee
        )

        self.instruction_volume_fee_1 = mommy.make(
            InstructionVolumeFee,
            client_org=self.client_organisation,
            max_volume_band_lowest=10000,
            max_volume_band_low=20000,
            max_volume_band_medium=50000,
            max_volume_band_top=100000,
            fee_rate_lowest=20,
            fee_rate_low=18,
            fee_rate_medium=15,
            fee_rate_top=10,
            fee_rate_type=FEE_CLAIMS_TYPE,
            vat=20
        )

        self.instruction_volume_fee_3 = mommy.make(
            InstructionVolumeFee,
            client_org=self.client_organisation,
            max_volume_band_lowest=10000,
            max_volume_band_low=20000,
            max_volume_band_medium=50000,
            max_volume_band_top=100000,
            fee_rate_lowest=20,
            fee_rate_low=18,
            fee_rate_medium=15,
            fee_rate_top=10,
            fee_rate_type=FEE_SARS_TYPE,
            vat=20
        )


class CalculateInstructionFeeTest(CalculateInstructionFeeBaseTest):

    def test_calculate_fee_amra(self):
        calculate_instruction_fee(self.amra_instruction)
        self.assertEqual(self.amra_instruction.gp_earns, 70)
        self.assertEqual(self.amra_instruction.medi_earns, 24)

    def test_calculate_fee_sars(self):
        calculate_instruction_fee(self.sars_instruction)
        self.assertEqual(self.sars_instruction.gp_earns, 0)
        self.assertEqual(self.sars_instruction.medi_earns, 24)
