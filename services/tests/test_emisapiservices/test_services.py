from datetime import date, datetime
from django.test import TestCase
from django.shortcuts import reverse

from model_mommy import mommy

from services.emisapiservices.services import (
    EmisAPIServiceBase, GetAttachment, GetPatientList, GetMedicalRecord
)
from instructions.models import InstructionPatient, Instruction, SARS_TYPE
from medicalreport.tests.test_views import EmisAPITestCase
from organisations.models import OrganisationGeneralPractice
from accounts.models import User, GENERAL_PRACTICE_USER, GeneralPracticeUser
from instructions.model_choices import INSTRUCTION_STATUS_PROGRESS

from django.conf import settings
EMIS_API_HOST = settings.EMIS_API_HOST


def generate_emis_api_config():
    return mommy.make(
        OrganisationGeneralPractice,
        operating_system_username='emis_username',
        operating_system_organisation_code='emis_id',
        _operating_system_salt_and_encrypted_password='password'
    )


class EmisAPIServiceBaseTest(TestCase):
    def setUp(self):
        gp = generate_emis_api_config()
        self.emis_api_service_base = EmisAPIServiceBase(gp)

    def test_uri_raises_error(self):
        self.assertRaises(NotImplementedError, self.emis_api_service_base.uri)


class GetAttachmentTest(TestCase):
    def setUp(self):
        gp = generate_emis_api_config()
        self.get_attachment = GetAttachment(
            patient_number='P123', attachment_identifier='attachment id', gp_organisation=gp
        )

    def test_uri(self):
        expected = f'{EMIS_API_HOST}/api/organisations/emis_id/patients/P123/attachments/attachment%20id'
        self.assertEqual(self.get_attachment.uri(), expected)


class GetPatientListTest(TestCase):
    def setUp(self):
        gp = generate_emis_api_config()
        patient = mommy.make(
            InstructionPatient,
            patient_first_name='first_name',
            patient_last_name='last_name',
            patient_dob=date(1990, 1, 2)
        )
        self.get_patient_list = GetPatientList(patient, gp_organisation=gp)
        blank_patient = mommy.make(
            InstructionPatient,
            patient_first_name='',
            patient_last_name='',
            patient_dob=None
        )
        self.get_patient_list_blank = GetPatientList(blank_patient, gp_organisation=gp)

        self.instruction_patient = mommy.make(
            InstructionPatient,
            patient_first_name='sarah',
            patient_last_name='giles',
            patient_dob=datetime.strptime('21091962', '%d%m%Y').date()
        )

        self.gp_practice = mommy.make(
            OrganisationGeneralPractice,
            practcode='TEST0001',
            name='Test Surgery',
            operating_system_organisation_code=29390,
            operating_system_username='failusername',
            operating_system_salt_and_encrypted_password='failpass',
        )
        self.gp_user = mommy.make(User, email='gp_user1@gmail.com', password='test1234', type=GENERAL_PRACTICE_USER, )
        self.gp_manager = mommy.make(
            GeneralPracticeUser,
            user=self.gp_user,
            organisation=self.gp_practice,
            role=GeneralPracticeUser.PRACTICE_MANAGER
        )
        self.instruction = mommy.make(
            Instruction,
            gp_user=self.gp_manager,
            patient_information=self.instruction_patient,
            type=SARS_TYPE,
            status=INSTRUCTION_STATUS_PROGRESS,
            gp_practice=self.gp_practice
        )

    def test_search_term(self):
        self.assertEqual(
            self.get_patient_list.search_term(),
            'first_name%20last_name%2002%2F01%2F1990'
        )

    def test_search_term_with_blank_fields(self):
        self.assertEqual(self.get_patient_list_blank.search_term(), '')

    def test_uri(self):
        expected = f'{EMIS_API_HOST}/api/organisations/emis_id/patients?q=first_name%20last_name%2002%2F01%2F1990'
        self.assertEqual(self.get_patient_list.uri(), expected)

    def test_call_emis_fail(self):
        self.client.force_login(self.gp_user)
        response = self.client.get(
            reverse('medicalreport:set_patient_emis_number', args=(self.instruction.id, ))
        )

        error_code_status = GetPatientList(self.instruction_patient, gp_organisation=self.gp_practice).call()

        self.assertEqual(302, response.status_code)
        self.assertEqual(401, error_code_status)


class GetMedicalRecordTest(EmisAPITestCase):
    def setUp(self):
        gp = generate_emis_api_config()
        self.get_medical_record = GetMedicalRecord(patient_number='P123', gp_organisation=gp)

    def test_uri(self):
        expected = f'{EMIS_API_HOST}/api/organisations/emis_id/patients/P123/medical_record'
        self.assertEqual(self.get_medical_record.uri(), expected)
