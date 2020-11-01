from django.test import RequestFactory, TestCase
from django.utils import timezone
from django.shortcuts import reverse

from instructions.models import Instruction, InstructionPatient
from instructions.model_choices import INSTRUCTION_STATUS_COMPLETE, AMRA_TYPE
from report.models import PatientReportAuth
from organisations.models import OrganisationClient, OrganisationGeneralPractice
from accounts.models import ClientUser, GeneralPracticeUser, User, GENERAL_PRACTICE_USER, Patient

from report.views import sar_request_code

from model_mommy import mommy


class reportAuthTestCase(TestCase):
    def setUp(self):
        # prepare data for create component instructions
        self.client_name = 'Test Trading Name Client Organisation'
        self.patient_first_name = 'Snoopy'
        self.patient_last_name = 'original'
        self.gp_user_name = 'gpuser'
        self.gp_earns = '500.00'
        self.date_instructions = timezone.now()

        # prepare request
        self.request = RequestFactory()

        # create client org.
        self.client_organisation = mommy.make(OrganisationClient, trading_name=self.client_name)
        
        # create client user
        self.client_user = mommy.make(
            ClientUser, organisation=self.client_organisation,
            role=ClientUser.CLIENT_MANAGER,
        )

        # create gp org. & gp user.
        self.gp_practice = mommy.make(OrganisationGeneralPractice, name='Test GP Practice', practcode='TEST0001')
        self.user = mommy.make(User, username=self.gp_user_name, first_name=self.gp_user_name)
        self.gp_user = mommy.make(
            GeneralPracticeUser,
            organisation=self.gp_practice,
            user=self.user,
            role=0,
            title='DR'
        )
        
        # create patient user and instructions
        self.patient = mommy.make(Patient, organisation_gp=self.gp_practice)
        self.instruction_patient = mommy.make(
            InstructionPatient,
            patient_title='MR',
            patient_first_name=self.patient_first_name,
            patient_last_name=self.patient_last_name
        )

        # create instructions
        self.instruction = mommy.make(
            Instruction, gp_practice=self.gp_practice, client_user=self.client_user, type=AMRA_TYPE, patient_information=self.instruction_patient,
            gp_user=self.gp_user, gp_earns=self.gp_earns, medi_earns=100, status=INSTRUCTION_STATUS_COMPLETE, completed_signed_off_timestamp=timezone.now()
        )

        # create report auth.
        self.url = 'kamomanez555'
        self.reportAuth = mommy.make(PatientReportAuth, patient=self.patient, instruction=self.instruction, url=self.url)

    # Test de-activate report
    def test_sar_request_code_lock(self):
        instruction = self.instruction
        instruction.deactivated = True
        instruction.save()

        response = self.client.get(reverse('report:request-code',
                    kwargs={'instruction_id': self.instruction.id, 'access_type': PatientReportAuth.ACCESS_TYPE_PATIENT, 'url': self.url}))
        self.assertTemplateUsed(response, 'de_activate.html')
        self.assertEqual(response.status_code, 200)

    def test_sar_request_code(self):
        response = self.client.get(reverse('report:request-code',
                    kwargs={'instruction_id': self.instruction.id, 'access_type': PatientReportAuth.ACCESS_TYPE_PATIENT, 'url': self.url}))
        self.assertTemplateUsed(response, 'patient/auth_1.html')
        self.assertEqual(response.status_code, 200)
