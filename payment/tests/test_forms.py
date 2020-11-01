from django.test import TestCase
from django.forms import ValidationError

from payment.forms import InstructionVolumeFeeForm
from payment.model_choices import FEE_SARS_TYPE
from organisations.models import OrganisationClient


class InstructionVolumeFeeFormTest(TestCase):

    def setUp(self):
        self.organisation_client_1 = OrganisationClient.objects.create(
            trading_name='Insurance company 1',
            legal_name='Insurance company 1',
            address='address',
            type=OrganisationClient.INSURER
        )
        self.organisation_client_invalid = [
            OrganisationClient.objects.create(
                trading_name='Insurance company 2',
                legal_name='Insurance company 2',
                address='address',
                type=OrganisationClient.INSURER
            ),
            OrganisationClient.objects.create(
                trading_name='Insurance company 3',
                legal_name='Insurance company 3',
                address='address',
                type=OrganisationClient.INSURER
            ),
            OrganisationClient.objects.create(
                trading_name='Insurance company 4',
                legal_name='Insurance company 4',
                address='address',
                type=OrganisationClient.INSURER
            ),
            OrganisationClient.objects.create(
                trading_name='Insurance company 5',
                legal_name='Insurance company 5',
                address='address',
                type=OrganisationClient.INSURER
            ),
            OrganisationClient.objects.create(
                trading_name='Insurance company 6',
                legal_name='Insurance company 6',
                address='address',
                type=OrganisationClient.INSURER
            ),
            OrganisationClient.objects.create(
                trading_name='Insurance company 7',
                legal_name='Insurance company 7',
                address='address',
                type=OrganisationClient.INSURER
            )
        ]

    def test_valid_data(self):
        form = InstructionVolumeFeeForm(
            {
                'client_org': self.organisation_client_1,
                'max_volume_band_lowest': 10000,
                'max_volume_band_low': 20000,
                'max_volume_band_medium': 50000,
                'max_volume_band_high': 60000,
                'max_volume_band_top': 100000,
                'fee_rate_lowest': 20,
                'fee_rate_low': 18,
                'fee_rate_medium': 15,
                'fee_rate_high': 13,
                'fee_rate_top': 10,
                'fee_rate_type': FEE_SARS_TYPE,
                'vat': 20
            },
        )
        self.assertTrue(form.is_valid())

    def test_invalid_band_data(self):
        invalid_band_case = [
            # band_lowest_>_band_low_case
            {
                'max_volume_band_lowest': 20000,
                'max_volume_band_low': 10000,
                'max_volume_band_medium': 50000,
                'max_volume_band_top': 100000,
            },
            # band_lowest_>_band_medium_case'
            {
                'max_volume_band_lowest': 10000,
                'max_volume_band_low': 20000,
                'max_volume_band_medium': 8000,
                'max_volume_band_top': 100000,
            },
            # band_lowest_>_band_top_case
            {
                'max_volume_band_lowest': 10000,
                'max_volume_band_low': 20000,
                'max_volume_band_medium': 50000,
                'max_volume_band_top': 8000,
            },
            # band_low_>_band_medium_case
            {
                'max_volume_band_lowest': 10000,
                'max_volume_band_low': 50000,
                'max_volume_band_medium': 20000,
                'max_volume_band_top': 100000,
            },
            # band_low_>_band_top_case
            {
                'max_volume_band_lowest': 10000,
                'max_volume_band_low': 20000,
                'max_volume_band_medium': 50000,
                'max_volume_band_top': 15000,
            },
            # band_medium_>_band_top_case
            {
                'max_volume_band_lowest': 10000,
                'max_volume_band_low': 20000,
                'max_volume_band_medium': 100000,
                'max_volume_band_top': 50000,
            },
        ]
        for case, client_organisation in zip(invalid_band_case, self.organisation_client_invalid):
            form = InstructionVolumeFeeForm(
                {
                    'client_org': client_organisation,
                    'max_volume_band_lowest': case['max_volume_band_lowest'],
                    'max_volume_band_low': case['max_volume_band_low'],
                    'max_volume_band_medium': case['max_volume_band_medium'],
                    'max_volume_band_top': case['max_volume_band_top'],
                    'fee_rate_lowest': 20,
                    'fee_rate_low': 18,
                    'fee_rate_medium': 15,
                    'fee_rate_top': 10,
                    'vat': 20,
                }
            )
            self.assertFalse(form.is_valid())
