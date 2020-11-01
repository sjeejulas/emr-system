from django.test import TestCase, Client, RequestFactory
from django.shortcuts import reverse
from django_tables2 import RequestConfig
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile

from model_mommy import mommy
from snomedct.models import SnomedConcept, CommonSnomedConcepts
from accounts.models import User, ClientUser, Patient, GeneralPracticeUser
from accounts import models as account_models
from instructions.models import Instruction, InstructionAdditionQuestion, \
                                InstructionConditionsOfInterest, Setting, \
                                InstructionPatient
from instructions.model_choices import *
from organisations.models import OrganisationGeneralPractice, OrganisationClient
from instructions.tables import InstructionTable
from instructions.views import count_instructions, calculate_next_prev, create_addition_question, create_snomed_relations
from instructions.forms import AdditionQuestionFormset
from medicalreport.tests.test_data.medical_file import MEDICAL_REPORT_WITH_ATTACHMENT_BYTES, MEDICAL_REPORT_BYTES, RAW_MEDICAL_XML

from datetime import datetime
from unittest.mock import Mock

medical_report = SimpleUploadedFile('report.pdf', b'consent')
medical_xml_report = SimpleUploadedFile('report.xml', b'<MedicalRecord></MedicalRecord>')


class TestInstructionBase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.gp_practice_1 = mommy.make(
            OrganisationGeneralPractice,
            practcode='TEST0001',
            name='Test Surgery',
            operating_system_organisation_code=29390,
            operating_system_username='michaeljtbrooks',
            operating_system_salt_and_encrypted_password='Medidata2019',
        )
        self.gp_user = mommy.make(User, email='gp_user1@gmail.com', password='test1234', type=account_models.GENERAL_PRACTICE_USER)
        self.gp_manager_1 = mommy.make(
            GeneralPracticeUser,
            user=self.gp_user,
            organisation=self.gp_practice_1,
            role=GeneralPracticeUser.PRACTICE_MANAGER
        )

        self.client_organisation = mommy.make(
            OrganisationClient,
            trading_name='Test Client Organisation',
            legal_name='Test Client Organisation',
            address='East 143 Railway Street ARMAGH BT61 7HT',
            type=OrganisationClient.OUTSOURCER,
        )
        self.client_user = mommy.make(User, email='client_user1@gmail.com', password='test1234', type=account_models.CLIENT_USER)
        self.client_admin_1 = mommy.make(ClientUser, user=self.client_user, organisation=self.client_organisation)

        self.instruction_patient_1 = mommy.make(
            InstructionPatient,
            patient_title='MR',
            patient_first_name='Sarah',
            patient_last_name='Giles',
            patient_dob=datetime.strptime('21091962', '%d%m%Y').date(),
            patient_dob_day='21',
            patient_dob_month='9',
            patient_dob_year='1962',
            patient_postcode='TA10 0AE',
            patient_address_number='Park Farm, Hambridge, Langport, Langport',
            patient_address_line1='Park Farm',
            patient_city='Langport',
            patient_county='Langport',
            patient_nhs_number='1111111111',
            patient_email='sarah@gmail.com',
        )
        self.instruction_patient_2 = mommy.make(
            InstructionPatient,
            patient_title='MR',
            patient_first_name='Benson',
            patient_last_name='John',
            patient_dob=datetime.strptime('01041957', '%d%m%Y').date(),
            patient_dob_day='01',
            patient_dob_month='04',
            patient_dob_year='1957',
            patient_postcode='TA10 0AE',
            patient_address_number='Park Farm, Hambridge, Langport, Langport',
            patient_address_line1='Park Farm',
            patient_city='Langport',
            patient_county='Langport',
            patient_nhs_number='2222222222',
            patient_email='benson@gmail.com',
        )
        self.instruction_patient_3 = mommy.make(
            InstructionPatient,
            patient_title='MR',
            patient_first_name='Alan',
            patient_last_name='Chatterly',
            patient_dob=datetime.strptime('07101950', '%d%m%Y').date(),
            patient_dob_day='07',
            patient_dob_month='10',
            patient_dob_year='1950',
            patient_postcode='TA10 0AE',
            patient_address_number='Park Farm, Hambridge, Langport, Langport',
            patient_address_line1='Park Farm',
            patient_city='Langport',
            patient_county='Langport',
            patient_nhs_number='3333333333',
            patient_email='alan@gmail.com',
        )
        self.instruction_1 = mommy.make(
            Instruction,
            client_user=self.client_admin_1,
            gp_user=self.gp_manager_1,
            patient_information=self.instruction_patient_1,
            type=SARS_TYPE,
            status=INSTRUCTION_STATUS_PROGRESS,
            gp_practice=self.gp_practice_1,
            medical_report=medical_report,
            medical_xml_report=medical_xml_report,
            medical_report_byte=MEDICAL_REPORT_BYTES,
            medical_with_attachment_report_byte=MEDICAL_REPORT_WITH_ATTACHMENT_BYTES,
        )
        self.instruction_2 = mommy.make(
            Instruction,
            client_user=self.client_admin_1,
            gp_user=self.gp_manager_1,
            patient_information=self.instruction_patient_2,
            type=AMRA_TYPE,
            status=INSTRUCTION_STATUS_NEW,
            gp_practice=self.gp_practice_1,
            medical_report=medical_report,
            medical_xml_report=medical_xml_report,
            medical_report_byte=MEDICAL_REPORT_BYTES,
            medical_with_attachment_report_byte=MEDICAL_REPORT_WITH_ATTACHMENT_BYTES,
        )
        self.instruction_3 = mommy.make(
            Instruction,
            client_user=None,
            gp_user=self.gp_manager_1,
            patient_information=self.instruction_patient_3,
            type=SARS_TYPE,
            status=INSTRUCTION_STATUS_COMPLETE,
            gp_practice=self.gp_practice_1,
            medical_report=medical_report,
            medical_xml_report=medical_xml_report,
            medical_report_byte=MEDICAL_REPORT_BYTES,
            medical_with_attachment_report_byte=MEDICAL_REPORT_WITH_ATTACHMENT_BYTES,
        )


class TestCountInstructions(TestInstructionBase):
    def test_count_instructions_of_gp_organisation(self):
        result = count_instructions(self.gp_user, self.gp_practice_1.pk, None, page='pipeline_view')
        expected = {
            'All': 3,
            'New': 1,
            'Redacting': 0,
            'In Progress': 1,
            'Paid': 0,
            'Completed': 1,
            'Rejected': 0,
            'Finalising': 0,
            'Rerun': 0
        }
        self.assertDictEqual(expected, result)

    def test_count_instructions_of_client_organisations(self):
        result = count_instructions(self.client_user, None, self.client_organisation, page='pipeline_view')
        expected = {
            'All': 2,
            'New': 1,
            'Redacting': 0,
            'In Progress': 1,
            'Paid': 0,
            'Completed': 0,
            'Rejected': 0,
            'Finalising': 0,
            'Rerun': 0
        }
        self.assertDictEqual(expected, result)


class TestCalculateNextPrev(TestInstructionBase):

    def test_calculate_next_prev(self):
        request = self.factory.get(reverse('instructions:view_pipeline'))
        table = InstructionTable(Instruction.objects.all())
        RequestConfig(request, paginate={'per_page': 5}).configure(table)
        result = calculate_next_prev(table.page, filter_status=INSTRUCTION_STATUS_NEW, filter_type=SARS_TYPE)

        expected = {
            'next_page': 1,
            'prev_page': 1,
            'status': 0,
            'page_length': None,
            'type': 'SARS',
            'next_disabled': 'disabled',
            'prev_disabled': 'disabled',
        }

        self.assertDictEqual(expected, result)


class TestCreateInstruction(TestInstructionBase):

    def test_get_new_instruction_client_user(self):
        self.client.force_login(self.client_user)
        response = self.client.get(reverse('instructions:new_instruction'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'instructions/new_instruction.html')

        self.client.logout()

    def test_get_new_instruction_gp_user(self):
        self.client.force_login(self.gp_user)
        response = self.client.get(reverse('instructions:new_instruction'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'instructions/new_instruction.html')

    def test_post_new_instruction_client_user(self):
        post_data = {
            'patient_title': 'MR',
            'patient_first_name': 'john',
            'patient_last_name': 'giles',
            'patient_dob_day': '21',
            'patient_dob_month': '9',
            'patient_dob_year': '1962',
            'patient_postcode': 'TA10 0AB',
            'patient_address_number': 'Far End Cottage, Curry Rivel, Langport, Somerset',
            'patient_address_line1': 'Far End Cottage',
            'patient_city': 'Langport',
            'patient_county': 'Somerset',
            'patient_nhs_number': '11111111',
            'patient_email': 'sarah@gmail.com',
            'gp_practice': 'TEST0001',
            'gp_practice_name': 'Test Surgery',
            'gp_title': 'DR',
            'initial': 'aaaa',
            'gp_last_name': 'Man',
            'type': 'AMRA',
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-question': 'question 1'
        }
        self.client.force_login(self.client_user)
        response = self.client.post(reverse('instructions:new_instruction'), post_data)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(Instruction.objects.filter(patient_information__patient_first_name='john').exists())
        new_instruction = Instruction.objects.get(patient_information__patient_first_name='john')
        self.assertEqual(new_instruction.type, AMRA_TYPE)
        self.assertEqual(new_instruction.gp_title_from_client, 'DR')
        self.assertEqual(new_instruction.gp_initial_from_client, 'aaaa')
        self.assertEqual(new_instruction.gp_last_name_from_client, 'Man')
        self.assertEqual(new_instruction.client_user, self.client_admin_1)
        self.assertEqual(new_instruction.gp_practice, self.gp_practice_1)

        patient_info = new_instruction.patient_information
        self.assertEqual(patient_info.patient_title, 'MR')
        self.assertEqual(patient_info.patient_first_name, 'john')
        self.assertEqual(patient_info.patient_last_name, 'giles')
        self.assertEqual(patient_info.patient_dob_day, '21')
        self.assertEqual(patient_info.patient_dob_month, '9')
        self.assertEqual(patient_info.patient_dob_year, '1962')
        self.assertEqual(patient_info.patient_postcode, 'TA10 0AB')
        self.assertEqual(patient_info.patient_address_number, 'Far End Cottage, Curry Rivel, Langport, Somerset')
        self.assertEqual(patient_info.patient_address_line1, 'Far End Cottage')
        self.assertEqual(patient_info.patient_city, 'Langport')
        self.assertEqual(patient_info.patient_county, 'Somerset')
        self.assertEqual(patient_info.patient_nhs_number, '11111111')
        self.assertEqual(patient_info.patient_email, 'sarah@gmail.com')

    def test_post_new_instruction_gp_user(self):
        post_data = {
            'patient_title': 'MR',
            'patient_first_name': 'Sam',
            'patient_last_name': 'Rich',
            'patient_dob_day': '21',
            'patient_dob_month': '9',
            'patient_dob_year': '1962',
            'patient_postcode': 'TA10 0AB',
            'patient_address_number': 'Far End Cottage, Curry Rivel, Langport, Somerset',
            'patient_address_line1': 'Far End Cottage',
            'patient_city': 'Langport',
            'patient_county': 'Somerset',
            'patient_nhs_number': '11111111',
            'patient_email': 'sam@gmail.com',
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
        }

        self.client.force_login(self.gp_user)
        response = self.client.post(reverse('instructions:new_instruction'), post_data)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(Instruction.objects.filter(patient_information__patient_first_name='Sam').exists())
        new_instruction = Instruction.objects.get(patient_information__patient_first_name='Sam')
        self.assertEqual(new_instruction.type, SARS_TYPE)
        self.assertEqual(new_instruction.gp_practice, self.gp_practice_1)

        patient_info = new_instruction.patient_information
        self.assertEqual(patient_info.patient_title, 'MR')
        self.assertEqual(patient_info.patient_first_name, 'Sam')
        self.assertEqual(patient_info.patient_last_name, 'Rich')
        self.assertEqual(patient_info.patient_dob_day, '21')
        self.assertEqual(patient_info.patient_dob_month, '9')
        self.assertEqual(patient_info.patient_dob_year, '1962')
        self.assertEqual(patient_info.patient_postcode, 'TA10 0AB')
        self.assertEqual(patient_info.patient_address_number, 'Far End Cottage, Curry Rivel, Langport, Somerset')
        self.assertEqual(patient_info.patient_address_line1, 'Far End Cottage')
        self.assertEqual(patient_info.patient_city, 'Langport')
        self.assertEqual(patient_info.patient_county, 'Somerset')
        self.assertEqual(patient_info.patient_nhs_number, '11111111')
        self.assertEqual(patient_info.patient_email, 'sam@gmail.com')


class TestCreateAdditionQuestion(TestInstructionBase):
    def setUp(self):
        super().setUp()
        self.addition_question_formset = AdditionQuestionFormset(
            {
                'form-TOTAL_FORMS': '1',
                'form-INITIAL_FORMS': '0',
                'form-MIN_NUM_FORMS': '0',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-question': ' Test Question 1'
            }
        )

    def test_create_addition_question(self):
        create_addition_question(self.instruction_2, self.addition_question_formset)
        addition_question = InstructionAdditionQuestion.objects.filter(instruction=self.instruction_2)
        self.assertTrue(addition_question.exists())
        self.assertEqual(addition_question.count(), 1)
        self.assertEqual(addition_question.first().question, 'Test Question 1')


class TestCreateSnomedRelations(TestInstructionBase):
    def setUp(self):
        super().setUp()
        self.snome_heart = mommy.make(SnomedConcept, external_id='56265001', fsn_description='Hearth disease')
        self.snome_stroke = mommy.make(SnomedConcept, external_id='62914000', fsn_description='Stroke / cerebro vascular')

    def test_create_snomed_relations(self):
        create_snomed_relations(self.instruction_2, ['56265001','62914000'])

        instruction_conditions = InstructionConditionsOfInterest.objects.filter(instruction=self.instruction_2)
        self.assertTrue(instruction_conditions.exists())
        self.assertEqual(instruction_conditions.count(), 2)

        self.assertTrue(
            InstructionConditionsOfInterest.objects.filter(instruction=self.instruction_2, snomedct=self.snome_heart).exists()
        )
        self.assertTrue(
            InstructionConditionsOfInterest.objects.filter(instruction=self.instruction_2,
                                                           snomedct=self.snome_stroke).exists()
        )


class TestInstructionPipelineView(TestInstructionBase):
    def setUp(self):
        super().setUp()
        self.gp_user_2 = User.objects.create(email='gpmanager2@gmail.com', username='gpmanager2@gmail.com', password='test1234')
        self.gp_manager_2 = GeneralPracticeUser.objects.create(
            user=self.gp_user_2,
            title='DR',
            organisation=self.gp_practice_1,
            role=GeneralPracticeUser.PRACTICE_MANAGER
        )

    def test_view_url(self):
        self.client.force_login(self.gp_user_2)
        response = self.client.get(
            reverse('instructions:view_pipeline')
        )

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'instructions/pipeline_views_instruction.html')
        self.client.logout()


class TestAllcatedUserChange(TestInstructionBase):

    def setUp(self):
        super().setUp()

        self.gp_test_user = User.objects.create(
            email = 'gpmanager2@gmail.com',
            username = 'gpmanager2@gmail.com',
            password = 'test1234')
        self.gp_test_manager = GeneralPracticeUser.objects.create(
            user=self.gp_test_user,
            title='DR',
            organisation=self.gp_practice_1,
            role=GeneralPracticeUser.PRACTICE_MANAGER
        )

    def test_update_allocate_user(self):
        self.client.force_login(self.gp_user)

        post_params = {
            'instruction_id': str(self.instruction_2.id),
            'selected_gp_id': str(self.gp_test_manager.id)
        }
        response = self.client.post(
            reverse('instructions:update_gp_allocated_user'),
            post_params
        )

        self.assertEqual(302, response.status_code)


class TestReviewInstruction(TestInstructionBase):
    def setUp(self):
        super().setUp()
        self.instruction_4 = mommy.make(
            Instruction,
            status=INSTRUCTION_STATUS_REJECT,
            gp_user=self.gp_manager_1,
            gp_practice=self.gp_practice_1,
            medical_report=medical_report,
            medical_xml_report=medical_xml_report,
            medical_report_byte=MEDICAL_REPORT_BYTES,
            medical_with_attachment_report_byte=MEDICAL_REPORT_WITH_ATTACHMENT_BYTES,
            final_raw_medical_xml_report=RAW_MEDICAL_XML
        )

    def test_view_url(self):
        self.client.force_login(self.gp_user)
        response = self.client.get(reverse('instructions:review_instruction', args=(self.instruction_2.id, )))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'instructions/review_instruction.html')
        self.client.logout()

    def test_reject_view_url(self):
        self.client.force_login(self.gp_user)
        response = self.client.get(reverse('instructions:view_reject', args=(self.instruction_4.id, )))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'instructions/view_reject.html')
        self.client.logout()


class TestConsentContact(TestInstructionBase):
    def setUp(self):
        super().setUp()
        self.instruction_patient_5 = mommy.make(
            InstructionPatient,
            patient_title='MR',
            patient_first_name='Alan',
            patient_last_name='Chatterly',
            patient_dob=datetime.strptime('07101950', '%d%m%Y').date(),
            patient_dob_day='07',
            patient_dob_month='10',
            patient_dob_year='1950',
            patient_postcode='TA10 0AE',
            patient_address_number='Park Farm, Hambridge, Langport, Langport',
            patient_address_line1='Park Farm',
            patient_city='Langport',
            patient_county='Langport',
            patient_nhs_number='3333333333',
            patient_email='alan@gmail.com',
        )
        self.instruction_5 = mommy.make(
            Instruction,
            client_user=None,
            gp_user=self.gp_manager_1,
            patient_information=self.instruction_patient_5,
            type=SARS_TYPE,
            status=INSTRUCTION_STATUS_NEW,
            gp_practice=self.gp_practice_1
        )

    def test_get_consent_contact_view(self):
        self.client.force_login(self.gp_user)
        response = self.client.get(
            reverse('instructions:consent_contact', kwargs={
                'instruction_id': self.instruction_5.id,
                'patient_emis_number': 500137
            })
        )
        self.assertEqual(200, response.status_code)

    def test_post_consent_contact_save_and_view_pipeline(self):
        self.client.force_login(self.gp_user)
        mock_mdx_file = Mock(spec=File)
        response = self.client.post(
            reverse('instructions:consent_contact', kwargs={'instruction_id': self.instruction_5.id, 'patient_emis_number': 500137}),
            {
                'next_step': 'view_pipeline',
                'mdx_consent': mock_mdx_file,
                'mdx_consent_loaded': 'loaded',
                'patient_email': 'change@gmail.com',
                'patient_telephone_mobile': '1111111111',
                'proceed_option': '0'
            }
        )
        self.assertEqual(302, response.status_code)
        self.assertEqual(response.url, '/instruction/view-pipeline/')
        updated_instruction_patient_5 = InstructionPatient.objects.get(id=self.instruction_patient_5.id)
        updated_instruction_5 = Instruction.objects.get(id=self.instruction_5.id)
        self.assertEqual(updated_instruction_patient_5.patient_email, 'change@gmail.com')
        self.assertEqual(updated_instruction_patient_5.patient_telephone_mobile, '1111111111')
        self.assertIsNotNone(updated_instruction_5.mdx_consent)

    def test_consent_contact_proceed_to_report(self):
        self.client.force_login(self.gp_user)
        mock_consent_file = Mock(spec=File)
        mock_mdx_file = Mock(spec=File)
        response = self.client.post(
            reverse(
                'instructions:consent_contact',
                kwargs={'instruction_id': self.instruction_5.id, 'patient_emis_number': 500137}
            ),
            {
                'next_step': 'proceed',
                'mdx_consent': mock_mdx_file,
                'mdx_consent_loaded': 'loaded',
                'patient_email': 'alan@gmail.com',
                'patient_telephone_mobile': '1111111111',
                'proceed_option': '0',
                'send-to-third': ['on'],
                'email_2': 'gianttiny123@gmail.com', 
                'office_phone_number': '1111111111'
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/medicalreport/' + str(self.instruction_5.id) + '/select-patient/500137/')


class TestPrintMdxConsent(TestInstructionBase):

    def setUp(self):
        super().setUp()
        self.instruction_patient_6 = mommy.make(
            InstructionPatient,
            patient_title='MR',
            patient_first_name='Alan',
            patient_last_name='Chatterly',
            patient_dob=datetime.strptime('07101950', '%d%m%Y').date(),
            patient_dob_day='07',
            patient_dob_month='10',
            patient_dob_year='1950',
            patient_postcode='TA10 0AE',
            patient_address_number='Park Farm, Hambridge, Langport, Langport',
            patient_address_line1='Park Farm',
            patient_city='Langport',
            patient_county='Langport',
            patient_nhs_number='3333333333',
            patient_email='alan@gmail.com',
        )
        self.instruction_6 = mommy.make(
            Instruction,
            client_user=None,
            gp_user=self.gp_manager_1,
            patient_information=self.instruction_patient_6,
            type=SARS_TYPE,
            status=INSTRUCTION_STATUS_NEW,
            gp_practice=self.gp_practice_1,
        )

    def test_get_print_mdx_consent(self):
        self.client.force_login(self.gp_user)
        response = self.client.get(
            reverse(
                'instructions:print_mdx_consent',
                kwargs={'instruction_id': self.instruction_6.id, 'patient_emis_number': 500137}
            )
        )
        self.assertEqual(response.status_code, 200)
