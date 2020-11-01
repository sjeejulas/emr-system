from django.test import TestCase
from ..models import OrganisationFeeRate, InstructionVolumeFee
from model_mommy import mommy
from organisations.models import OrganisationGeneralPractice, OrganisationClient
from payment.model_choices import FEE_UNDERWRITE_TYPE


class OrganisationFeeModelTest(TestCase):

    def setUp(self):
        self.gp_practice = mommy.make(
            OrganisationGeneralPractice,
            name="Test Trading Name GP Organisation"
        )

        self.organisation_fee = mommy.make(
            OrganisationFeeRate,
            name='TEST BAND',
            max_day_lvl_1=3,
            max_day_lvl_2=6,
            max_day_lvl_3=8,
            max_day_lvl_4=9,
            amount_rate_lvl_1=70,
            amount_rate_lvl_2=50,
            amount_rate_lvl_3=30,
            amount_rate_lvl_4=20
        )

    def test_string_representation(self):
        self.assertEqual(
            str(self.organisation_fee), "{band_name}: Top payment band is {top_payment}".format(
                band_name=self.organisation_fee.name,
                top_payment=self.organisation_fee.amount_rate_lvl_1
            )
        )

    def test_verbose_name(self):
        self.assertEqual(str(OrganisationFeeRate._meta.verbose_name), "GP Organisation Fee Structure")

    def test_verbose_name_plural(self):
        self.assertEqual(str(OrganisationFeeRate._meta.verbose_name_plural), "GP Organisation Fee Structures")

    def test_get_fee_rate_method(self):
        fee_rate_1 = self.organisation_fee.get_fee_rate(2)
        fee_rate_2 = self.organisation_fee.get_fee_rate(5)
        fee_rate_3 = self.organisation_fee.get_fee_rate(7)
        fee_rate_4 = self.organisation_fee.get_fee_rate(9)

        self.assertEqual(fee_rate_1, 70)
        self.assertEqual(fee_rate_2, 50)
        self.assertEqual(fee_rate_3, 30)
        self.assertEqual(fee_rate_4, 20)

    def test_default_calendar_days(self):
        gp_practice = mommy.make(
            OrganisationGeneralPractice,
            name="GP organisation"
        )
        org_fee = OrganisationFeeRate.objects.create(
            amount_rate_lvl_1=60.00,
            amount_rate_lvl_2=51.00,
            amount_rate_lvl_3=43.35,
            amount_rate_lvl_4=36.85
        )

        self.assertEqual(org_fee.max_day_lvl_1, 3)
        self.assertEqual(org_fee.max_day_lvl_2, 7)
        self.assertEqual(org_fee.max_day_lvl_3, 11)
        self.assertEqual(org_fee.max_day_lvl_4, 12)


class InstructionVolumeFeeClientModelTest(TestCase):

    def setUp(self):
        self.client_organisation = mommy.make(
            OrganisationClient,
            trading_name='Test Trading Name Client Organisation'
        )

        self.instruction_volume_fee = mommy.make(
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
            fee_rate_type=2
        )

    def test_string_representation(self):
        self.assertEqual(str(self.instruction_volume_fee), "Fee Structure: {} - AMRA_UNDERWRITING".format(self.client_organisation))

    def test_verbose_name(self):
        self.assertEqual(str(InstructionVolumeFee._meta.verbose_name), "Client Instruction Volume Fee structure")

    def test_verbose_name_plural(self):
        self.assertEqual(str(InstructionVolumeFee._meta.verbose_name_plural), "Client Instruction Volume Fee structures")

    def test_get_fee_rate_method(self):
        fee_rate_1 = self.instruction_volume_fee.get_fee_rate(5000)
        fee_rate_2 = self.instruction_volume_fee.get_fee_rate(15000)
        fee_rate_3 = self.instruction_volume_fee.get_fee_rate(45000)
        fee_rate_4 = self.instruction_volume_fee.get_fee_rate(80000)

        self.assertEqual(fee_rate_1, 20)
        self.assertEqual(fee_rate_2, 18)
        self.assertEqual(fee_rate_3, 15)
        self.assertEqual(fee_rate_4, 10)
