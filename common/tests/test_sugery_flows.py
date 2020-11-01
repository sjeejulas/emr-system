from django.test import TestCase
from django.shortcuts import reverse
from accounts.models import User, CLIENT_USER, ClientUser
from organisations.models import OrganisationClient
from django.core.files import File
from django.core.management import call_command
from unittest.mock import Mock
from instructions.models import Instruction
from instructions.model_choices import INSTRUCTION_STATUS_FINALISE, INSTRUCTION_STATUS_RERUN, INSTRUCTION_STATUS_COMPLETE
from payment.models import OrganisationFeeRate
from django.test import tag


class SurgeryOnboard(TestCase):

    def setUp(self):
        self.practice_code = 'TESTSURGERY'
        self.emis_org_code = '29390'
        self.email = 'mohara@mohara.co'
        self.surgery_email = 'surgery@mohara.co'
        self.patient_email = 'patient@mohara.co'
        self.password = 'Surgery2018test'
        self.address = 'Aberdeen City Council, Director of Housing  St. Nicholas House, Broad Street, Aberdeen, Aberdeenshire'
        self.phone_number = '874432803'
        self.phone_code = '66'
        self.emis_number = '500139'
        self.patient_first_name = 'Sarah'
        self.patient_last_name = 'Giles'
        self.day_of_dob = '21'
        self.month_of_dob = '9'
        self.year_of_dob = '1962'
        self.create_fee()
        self.onboarding_step1()
        self.onboarding_step2()
        self.emis_polling()
        self.onboarding_step3()

    def create_fee(self):
        self.fee = OrganisationFeeRate.objects.create(
            name='Surgery Fee',
            amount_rate_lvl_1=70,
            amount_rate_lvl_2=60,
            amount_rate_lvl_3=50,
            amount_rate_lvl_4=40,
            default=True
        )

    def onboarding_step1(self):
        data = {
            'practice_code': self.practice_code,
            'surgery_name': 'TESTSURGERY',
            'accept_policy': 'on',
            'postcode': 'AB10 1AF',
            'address': self.address,
            'address_line1': 'Child Protection Partnership',
            'address_line2': 'Business Hub 2',
            'address_line3': 'Aberdeen',
            'city': 'Aberdeen',
            'consented': 'on',
            'contact_num': '29390',
            'county': 'Aberdeenshire',
            'emis_org_code': self.emis_org_code,
            'operating_system': 'EMISWeb',
            'organisation_email': 'test@test.com',
            'confirm_email': 'test@test.com',
        }
        response = self.client.post(reverse('onboarding:step1'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/onboarding/step-2/' + self.practice_code)

    def onboarding_step2(self):
        data = {
            'email1': self.email,
            'email2': self.email,
            'first_name': 'Surgery',
            'surname': 'Medi',
            'password1': self.password,
            'password2': self.password,
            'telephone_code': self.phone_code,
            'telephone_mobile': self.phone_number,
            'title': 'MR',
            'form-0-email': 'manager@mohara.co',
            'form-0-first_name': 'Manager',
            'form-0-last_name': 'GP',
            'form-0-mobile_code': self.phone_code,
            'form-0-mobile_phone': self.phone_number,
            'form-0-role': '0',
            'form-0-title': 'MR',
            'form-1-email': 'gp@mohara.co',
            'form-1-first_name': 'GP',
            'form-1-last_name': 'GP',
            'form-1-mobile_code': self.phone_code,
            'form-1-mobile_phone': self.phone_number,
            'form-1-role': '1',
            'form-1-title': 'MR',
            'form-2-email': 'other@mohara.co',
            'form-2-first_name': 'Other',
            'form-2-last_name': 'GP',
            'form-2-mobile_code': self.phone_code,
            'form-2-mobile_phone': self.phone_number,
            'form-2-role': '2',
            'form-2-title': 'MR',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-MIN_NUM_FORMS': '0',
            'form-TOTAL_FORMS': '3',
        }
        response = self.client.post(reverse('onboarding:step2', kwargs={'practice_code': self.practice_code}), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/onboarding/step-3/' + self.practice_code)

    def emis_polling(self):
        response = self.client.get(reverse('onboarding:emis_polling', kwargs={'practice_code':self.practice_code}))
        result = {'status': 200, 'practice_code': self.practice_code}
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), result)
        self.user = User.objects.get(email=self.email)
        self.client.force_login(self.user)

    def onboarding_step3(self):
        response = self.client.get(
            reverse('onboarding:step3', kwargs={'practice_code': self.practice_code})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/step3.html')


class SurgerySARSFlow(SurgeryOnboard):

    def setUp(self):
        super().setUp()
        self.create_sars()
        self.add_consent_contact()
        self.preview_report()
        self.submit_report()

    def create_sars(self):
        data = {
            'date_range_from': '',
            'date_range_to': '',
            'instruction_id': '',
            'patient_address_line1': 'Aberdeen City Council',
            'patient_address_line2': ' Finance Department  Town House',
            'patient_address_line3': ' Broad Street',
            'patient_address_number': self.address,
            'patient_city': ' Aberdeen',
            'patient_county': ' Aberdeenshire',
            'patient_dob_day': self.day_of_dob,
            'patient_dob_month': self.month_of_dob,
            'patient_dob_year': self.year_of_dob,
            'patient_first_name': self.patient_first_name,
            'patient_last_name': self.patient_last_name,
            'patient_nhs_number': '',
            'patient_postcode': 'AB10 1AH',
            'patient_title': 'MIS'
        }
        response = self.client.post(reverse('instructions:new_instruction'), data)
        self.instruction = Instruction.objects.filter(gp_user__user__pk=self.user.pk).first()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/medicalreport/' + str(self.instruction.pk) + '/patient-emis-number/')

    def add_consent_contact(self):
        mock_mdx_file = Mock(spec=File)
        data = {
            'confirm_email': self.patient_email,
            'mdx_consent_loaded': 'loaded',
            'mdx_consent': mock_mdx_file,
            'next_step': 'proceed',
            'patient_address_number': self.address,
            'patient_alternate_code': self.phone_code,
            'patient_alternate_phone': self.phone_number,
            'patient_dob': '/'.join([self.day_of_dob,self.month_of_dob,self.year_of_dob]),
            'patient_email': self.patient_email,
            'patient_first_name': self.patient_first_name,
            'patient_last_name': self.patient_last_name,
            'patient_nhs_number': '',
            'patient_postcode': 'AB10 1AF',
            'patient_telephone_code': self.phone_code,
            'patient_telephone_mobile': self.phone_number,
            'patient_title': 'Mr.',
            'sars_consent': '',
            'sars_consent_loaded': '',
            'proceed_option': '0'
        }
        response = self.client.post(reverse(
            'instructions:consent_contact',
            kwargs={'instruction_id':self.instruction.pk, 'patient_emis_number':self.emis_number})
        , data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/medicalreport/' + str(self.instruction.pk) + '/select-patient/' + self.emis_number + '/')
        response = self.client.get(reverse(
            'medicalreport:select_patient',
            kwargs={'instruction_id':self.instruction.pk, 'patient_emis_number':self.emis_number})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/medicalreport/' + str(self.instruction.pk) + '/edit/')

    def preview_report(self):
        data = {
            'additional_allergies_allergen': '',
            'additional_allergies_date_discovered': '',
            'additional_allergies_reaction': '',
            'additional_medication_dose': '',
            'additional_medication_drug': '',
            'additional_medication_frequency': '',
            'additional_medication_notes': '',
            'additional_medication_prescribed_from': '',
            'additional_medication_prescribed_to': '',
            'additional_medication_records_type': '',
            'additional_medication_related_condition': '',
            'event_flag': 'preview',
            'redaction_acute_prescription_notes': '',
            'redaction_attachment_notes': '',
            'redaction_bloods_notes': '',
            'redaction_comment_notes': '',
            'redaction_consultation_notes': '',
            'redaction_referral_notes': '',
            'redaction_repeat_prescription_notes': '',
            'redaction_significant_problem_notes': '',
            'redaction_xpaths': None
        }
        response = self.client.post(reverse('medicalreport:update_report', kwargs={'instruction_id':self.instruction.pk}), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/medicalreport/' + str(self.instruction.pk) + '/submit-report/')

    def submit_report(self):
        data = {
            'event_flag': 'submit',
            'prepared_and_signed': 'PREPARED_AND_REVIEWED',
            'prepared_by': '1'
        }
        response = self.client.post(reverse('medicalreport:update_report', kwargs={'instruction_id':self.instruction.pk}), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/instruction/view-pipeline/')

    @tag('end_to_end')
    def test_instruction_files(self):
        instruction = Instruction.objects.get(pk=self.instruction.pk)

        if instruction.status not in [INSTRUCTION_STATUS_FINALISE, INSTRUCTION_STATUS_RERUN, INSTRUCTION_STATUS_COMPLETE]:
            self.fail("Instruction invalid status")


class SurgeryAMRAFlow(SurgeryOnboard):

    def setUp(self):
        super().setUp()
        self.create_client()
        self.import_data()
        self.create_amra()
        self.select_patient()
        self.preview_report()
        self.submit_report()

    def create_client(self):
        self.client_org = OrganisationClient.objects.create(
            type=OrganisationClient.OUTSOURCER
        )
        self.client_user = User.objects.create(
            email='client@mohara.co',
            type=CLIENT_USER
        )
        self.client_profile = ClientUser.objects.create(
            role=ClientUser.CLIENT_MANAGER,
            organisation=self.client_org,
            user=self.client_user,
            title='MR'
        )

    def import_data(self):
        call_command('import_snomedct', '--snomed_concepts', verbosity=0)
        call_command('loaddata', 'config/data/common.json', verbosity=0)

    def create_amra(self):
        self.client.force_login(self.client_user)
        mock_consent_form = Mock(spec=File)
        data = {
            'addition_condition_title': '',
            'common_condition': '[126951006]',
            'date_range_from': '',
            'date_range_to': '',
            'form-0-question': '',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-MIN_NUM_FORMS': '0',
            'form-TOTAL_FORMS': '1',
            'gp_last_name': 'GP',
            'gp_practice': self.practice_code,
            'gp_practice_name': 'Surgery',
            'gp_title': 'MR',
            'initial': 'Pichate',
            'instruction_id': '',
            'medi_ref': '10000040',
            'patient_address_line1': 'Aberdeen City Council',
            'patient_address_line2': ' Education Department  St. Nicholas House',
            'patient_address_line3': ' Broad Street',
            'patient_address_number': self.address,
            'patient_city': ' Aberdeen',
            'patient_county': ' Aberdeenshire',
            'patient_dob_day': '21',
            'patient_dob_month': '9',
            'patient_dob_year': '1962',
            'patient_email': '',
            'patient_first_name': 'Sarah',
            'patient_last_name': 'Giles',
            'patient_nhs_number': '',
            'patient_postcode': 'AB10 1AG',
            'patient_title': 'MR',
            'template': '',
            'type': 'AMRA',
            'your_ref': 'REF001',
            'consent_form': mock_consent_form
        }
        response = self.client.post(reverse('instructions:new_instruction'), data)
        self.instruction = Instruction.objects.filter(client_user__user__pk=self.client_user.pk).first()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/instruction/view-pipeline/')

    def select_patient(self):
        self.client.force_login(self.user)
        data = {
            'allocate_options': '0',
            'gp_practitioner': ''
        }
        response = self.client.post(reverse(
            'medicalreport:select_patient',
            kwargs={'instruction_id':self.instruction.pk, 'patient_emis_number':self.emis_number}),
            data
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/medicalreport/' + str(self.instruction.pk) + '/edit/')

    def preview_report(self):
        data = {
            'additional_allergies_allergen': '',
            'additional_allergies_date_discovered': '',
            'additional_allergies_reaction': '',
            'additional_medication_dose': '',
            'additional_medication_drug': '',
            'additional_medication_frequency': '',
            'additional_medication_notes': '',
            'additional_medication_prescribed_from': '',
            'additional_medication_prescribed_to': '',
            'additional_medication_records_type': '',
            'additional_medication_related_condition': '',
            'event_flag': 'preview',
            'redaction_acute_prescription_notes': '',
            'redaction_attachment_notes': '',
            'redaction_bloods_notes': '',
            'redaction_comment_notes': '',
            'redaction_consultation_notes': '',
            'redaction_referral_notes': '',
            'redaction_repeat_prescription_notes': '',
            'redaction_significant_problem_notes': '',
            'redaction_xpaths': None
        }
        response = self.client.post(reverse('medicalreport:update_report', kwargs={'instruction_id':self.instruction.pk}), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/medicalreport/' + str(self.instruction.pk) + '/submit-report/')

    def submit_report(self):
        data = {
            'event_flag': 'submit',
            'prepared_and_signed': 'PREPARED_AND_REVIEWED',
            'prepared_by': '1'
        }
        response = self.client.post(reverse('medicalreport:update_report', kwargs={'instruction_id':self.instruction.pk}), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/instruction/view-pipeline/')

    @tag('end_to_end')
    def test_instruction_files(self):
        instruction = Instruction.objects.get(pk=self.instruction.pk)
        if not bytes(instruction.medical_report_byte):
            self.fail("Medical report is missing")
        if not instruction.final_raw_medical_xml_report:
            self.fail("Medical report xml is missing")
        if instruction.status not in [INSTRUCTION_STATUS_FINALISE, INSTRUCTION_STATUS_RERUN, INSTRUCTION_STATUS_COMPLETE]:
            self.fail("Instruction invalid status")
