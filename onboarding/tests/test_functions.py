from django.test import TestCase
from model_mommy import mommy

from organisations.models import OrganisationGeneralPractice
from payment.models import OrganisationFeeRate, GpOrganisationFee
from ..functions import create_gp_user, create_gp_payments_fee, update_gp_organisation_bank_details
from ..forms import BankDetailsEmrSetUpStage2Form

import decimal


class FunctionsOnboardingTest(TestCase):

    def setUp(self):
        self.organisation_fee = mommy.make(
            OrganisationFeeRate,
            name='TEST BAND',
            base=True,
            default=True
        )

        self.bank_detail_form = BankDetailsEmrSetUpStage2Form({
            'bank_account_name': 'Test Bank account Name',
            'bank_account_number': '11-22-33',
            'bank_account_sort_code': '123456',
            'received_within_3_days': self.organisation_fee.pk,
            'received_within_4_to_7_days': 50,
            'received_within_8_to_11_days': 40,
            'received_after_11_days': 30,
            'completed_by': 'Completer Man',
            'job_title': 'Tet Job Title'
        })
        self.gp_practice = mommy.make(OrganisationGeneralPractice, practcode='TEST0001', name='Test Surgery 01')

    def test_create_gp_user(self):
        pass

    def test_create_gp_payments_fee(self):
        self.assertEqual(True, self.bank_detail_form.is_valid())

        organisation_fee = create_gp_payments_fee(self.bank_detail_form, self.gp_practice)

        self.assertEqual(True, GpOrganisationFee.objects.filter(id=organisation_fee.id).exists())
        self.assertEqual(self.organisation_fee.amount_rate_lvl_1, organisation_fee.amount_rate_lvl_1)
        self.assertEqual(self.organisation_fee.amount_rate_lvl_2, organisation_fee.amount_rate_lvl_2)
        self.assertEqual(
            self.organisation_fee.amount_rate_lvl_3,
            organisation_fee.amount_rate_lvl_3
        )
        self.assertEqual(
            self.organisation_fee.amount_rate_lvl_4,
            organisation_fee.amount_rate_lvl_4
        )

    def test_update_gp_organisation_bank_details(self):
        self.assertEqual(True, self.bank_detail_form.is_valid())
        gp_practice = update_gp_organisation_bank_details(self.bank_detail_form, self.gp_practice)

        self.assertEqual(gp_practice.payment_bank_holder_name, 'Test Bank account Name')
        self.assertEqual(gp_practice.payment_bank_account_number, '11-22-33')
        self.assertEqual(gp_practice.payment_bank_sort_code, '123456')
        self.assertEqual(gp_practice.onboarding_by, 'Completer Man')
        self.assertEqual(gp_practice.onboarding_job_title, 'Tet Job Title')
