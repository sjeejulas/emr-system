from datetime import date, datetime

from django.test import TestCase
from django.http import JsonResponse
from django.shortcuts import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from model_mommy import mommy

from services.xml.medical_record import MedicalRecord
from instructions.models import Instruction, InstructionPatient
from instructions.model_choices import INSTRUCTION_STATUS_REJECT, INSTRUCTION_STATUS_PROGRESS,\
    INSTRUCTION_STATUS_COMPLETE, AMRA_TYPE
from accounts.models import User, GeneralPracticeUser, Patient, GENERAL_PRACTICE_USER
from snomedct.models import SnomedConcept
from medicalreport.models import AmendmentsForRecord, ReferencePhrases
from medicalreport.views import get_matched_patient
from organisations.models import OrganisationGeneralPractice
from .test_data.medical_file import MEDICAL_REPORT_WITH_ATTACHMENT_BYTES, MEDICAL_REPORT_BYTES, RAW_MEDICAL_XML
from report.models import PatientReportAuth
from medicalreport.templatetags.custom_filters import replace_ref_phrases
from library.models import Library, LibraryHistory

import os
import string, random
from contextlib import suppress


medical_report = SimpleUploadedFile('report.pdf', b'consent')
mdx_consent = SimpleUploadedFile('report.pdf', b'consent')
medical_with_attachment_report = SimpleUploadedFile('report.pdf', b'consent')
medical_xml_report = SimpleUploadedFile('report.xml', b'<MedicalRecord></MedicalRecord>')


class EmisAPITestCase(TestCase):
    def setUp(self):
        patient_user = mommy.make(
            User, first_name='Alan', last_name='Ball')
        self.patient = mommy.make(
            Patient, user=patient_user, emis_number='2985', date_of_birth=None)
        user = mommy.make(User, type=GENERAL_PRACTICE_USER)
        self.instruction_patient = mommy.make(
            InstructionPatient,
            patient_first_name='Alan',
            patient_last_name='Ball',
            patient_dob=None,
            patient_emis_number='2985'
        )
        gp_practice = mommy.make(
            OrganisationGeneralPractice, pk=1,
            name='GP Organisation',
            billing_address_street='99/99',
            billing_address_city='Bangkok',
            billing_address_postalcode='2510',
            gp_operating_system='OT',
            practcode='99999',
            operating_system_organisation_code=29390,
            operating_system_username='michaeljtbrooks',
            operating_system_salt_and_encrypted_password='Medidata2019',
        )
        self.gp_user = mommy.make(GeneralPracticeUser, user=user, organisation=gp_practice)
        self.gp_practice = gp_practice
        consent_form = SimpleUploadedFile('test_consent_form.txt', b'consent')
        self.instruction = mommy.make(
            Instruction, pk=1, consent_form=consent_form,
            patient=self.patient, gp_user=self.gp_user,
            gp_practice=gp_practice,
            patient_information=self.instruction_patient,
            mdx_consent=mdx_consent,
            medical_report=medical_report,
            medical_xml_report=medical_xml_report,
            medical_with_attachment_report=medical_with_attachment_report,
            medical_report_byte=MEDICAL_REPORT_BYTES,
            medical_with_attachment_report_byte=MEDICAL_REPORT_WITH_ATTACHMENT_BYTES,
            final_raw_medical_xml_report=RAW_MEDICAL_XML
        )
        self.aes_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
        self.redaction = mommy.make(
            AmendmentsForRecord, instruction=self.instruction, pk=1,
            raw_medical_xml_aes_key=self.aes_key,
            raw_medical_xml_encrypted=RAW_MEDICAL_XML
        )
        self.client.force_login(user, backend=None)

    def tearDown(self):
        with suppress(FileNotFoundError, AttributeError, ValueError):
            os.remove(self.instruction.consent_form.path)


class GetMatchedPatientTest(EmisAPITestCase):
    def test_get_matched_patient(self):
        registrations = get_matched_patient(self.instruction_patient, self.gp_practice)
        self.assertIn(
            'Mr Alan Ball',
            [registration.full_name() for registration in registrations]
        )


class RejectRequestTest(EmisAPITestCase):
    def setUp(self):
        super().setUp()
        consent_form = SimpleUploadedFile('test_consent_form.txt', b'consent')
        self.instruction = mommy.make(
            Instruction, pk=4, consent_form=consent_form,
            patient=self.patient, gp_user=self.gp_user,
            gp_practice=self.gp_practice, status=INSTRUCTION_STATUS_REJECT,
            medical_report=medical_report,
            medical_xml_report=medical_xml_report,
            medical_with_attachment_report=medical_with_attachment_report,
            medical_report_byte=MEDICAL_REPORT_BYTES,
            medical_with_attachment_report_byte=MEDICAL_REPORT_WITH_ATTACHMENT_BYTES,
            final_raw_medical_xml_report=RAW_MEDICAL_XML
        )
        self.redaction = mommy.make(
            AmendmentsForRecord, instruction=self.instruction, pk=4,
            raw_medical_xml_aes_key=self.aes_key,
            raw_medical_xml_encrypted=RAW_MEDICAL_XML
        )

    def test_view_url(self):
        response = self.client.post('/medicalreport/4/reject-request/')
        self.assertEqual(302, response.status_code)

    def test_view_url_by_name(self):
        response = self.client.post(
            reverse('medicalreport:reject_request', args=(4,))
        )
        self.assertEqual(302, response.status_code)

    def test_view_redirects_to_correct_url(self):
        response = self.client.post('/medicalreport/4/reject-request/')
        self.assertRedirects(
            response, '/instruction/view-pipeline/?status=%s&type=allType' % INSTRUCTION_STATUS_REJECT,
            status_code=302, target_status_code=302
        )


class SelectPatientTest(EmisAPITestCase):
    def test_view_url(self):
        response = self.client.get('/medicalreport/1/select-patient/2985/')
        self.assertEqual(302, response.status_code)

    def test_view_url_by_name(self):
        response = self.client.get(
            reverse('medicalreport:select_patient', args=(1, 2985))
        )
        self.assertEqual(302, response.status_code)

    def test_view_redirects_to_correct_url(self):
        response = self.client.get('/medicalreport/1/select-patient/2985/')
        self.assertEqual(302, response.status_code)
        self.assertRedirects(response, '/medicalreport/1/edit/')

    def test_instruction_status_is_set(self):
        self.assertNotEqual(INSTRUCTION_STATUS_PROGRESS, self.instruction.status)
        self.client.get('/medicalreport/1/select-patient/2985/')
        self.instruction.refresh_from_db()
        self.assertEqual(INSTRUCTION_STATUS_PROGRESS, self.instruction.status)

    def test_instruction_gp_user_is_set(self):
        self.instruction.gp_user = None
        self.instruction.save()
        self.client.get('/medicalreport/1/select-patient/2985/')
        self.instruction.refresh_from_db()
        self.assertEqual(self.gp_user, self.instruction.gp_user)

    def test_new_redaction_is_created(self):
        self.redaction.delete()
        self.assertEqual(0, AmendmentsForRecord.objects.count())
        self.client.get('/medicalreport/1/select-patient/2985/')
        self.assertEqual(1, AmendmentsForRecord.objects.count())

    def test_existing_redaction_is_used(self):
        self.assertEqual(1, AmendmentsForRecord.objects.count())
        self.client.get('/medicalreport/1/select-patient/2985/')
        self.assertEqual(1, AmendmentsForRecord.objects.count())

    def test_patient_emis_number_is_set_on_redaction(self):
        self.client.get('/medicalreport/1/select-patient/2985/')
        redaction = AmendmentsForRecord.objects.get()
        self.assertEqual('2985', redaction.patient_emis_number)

    def test_view_returns_302_if_gp_user_not_found(self):
        self.client.logout()
        response = self.client.get('/medicalreport/1/select-patient/2985/')
        self.assertEqual(302, response.status_code)


class SetPatientEmisNumberTest(EmisAPITestCase):
    def test_view_url(self):
        response = self.client.get('/medicalreport/1/patient-emis-number/')
        self.assertEqual(200, response.status_code)

    def test_view_url_by_name(self):
        response = self.client.get(
            reverse('medicalreport:set_patient_emis_number', args=(1,))
        )
        self.assertEqual(200, response.status_code)

    def test_view_uses_correct_template(self):
        response = self.client.get('/medicalreport/1/patient-emis-number/')
        self.assertTemplateUsed(
            response, 'medicalreport/patient_emis_number.html')


class EditReportTest(EmisAPITestCase):
    def setUp(self):
        super().setUp()
        consent_form = SimpleUploadedFile('test_consent_form.txt', b'consent')
        self.instruction_patient = mommy.make(
            InstructionPatient,
            patient_first_name='Alan',
            patient_last_name='Ball',
            patient_dob=None,
            patient_emis_number='2985'
        )
        self.instruction = mommy.make(
            Instruction, pk=2, consent_form=consent_form,
            patient_information=self.instruction_patient,
            patient=self.patient, gp_user=self.gp_user,
            gp_practice=self.gp_practice, status=INSTRUCTION_STATUS_PROGRESS, type='SARS',
            medical_report=medical_report,
            medical_xml_report=medical_xml_report,
            medical_with_attachment_report=medical_with_attachment_report,
            medical_report_byte=MEDICAL_REPORT_BYTES,
            medical_with_attachment_report_byte=MEDICAL_REPORT_WITH_ATTACHMENT_BYTES,
            final_raw_medical_xml_report=RAW_MEDICAL_XML,
            **{'date_range_from': datetime(1995, 10, 10), 'date_range_to': datetime(2015, 10, 10)}
        )

        self.snomed_concept = mommy.make(SnomedConcept, external_id=365981007)
        self.snomed_concept = mommy.make(SnomedConcept, external_id=228273003)
        self.redaction = mommy.make(
            AmendmentsForRecord, instruction=self.instruction, pk=2,
            raw_medical_xml_aes_key=self.aes_key,
            raw_medical_xml_encrypted=RAW_MEDICAL_XML
        )

    def test_view_url(self):
        response = self.client.get('/medicalreport/2/edit/')
        self.assertEqual(200, response.status_code)

    def test_view_url_by_name(self):
        response = self.client.get(
            reverse('medicalreport:edit_report', args=(2,))
        )
        self.assertEqual(200, response.status_code)

    def test_view_uses_correct_template(self):
        response = self.client.get('/medicalreport/2/edit/')
        self.assertTemplateUsed(
            response, 'medicalreport/medicalreport_edit.html')

    def test_view_returns_404_if_instruction_does_not_exist(self):
        response = self.client.get('/medicalreport/5/edit/')
        self.assertEqual(404, response.status_code)

    def test_view_redirects_if_redaction_does_not_exist(self):
        self.redaction.delete()
        response = self.client.get('/medicalreport/2/edit/')
        self.assertEqual(302, response.status_code)

    def test_view_profile_field_for_amra(self):
        response = self.client.get('/medicalreport/2/edit/')
        medical_record = response.context.get('medical_record')
        medical_record.instruction.type = "AMRA"
        test_data = medical_record.profile_events_by_type()
        self.assertListEqual(list(test_data.keys()), MedicalRecord.AMRA__PROFILE_EVENT_TYPES)

    def test_view_profile_field_for_sars(self):
        response = self.client.get('/medicalreport/2/edit/')
        medical_record = response.context.get('medical_record')
        medical_record.instruction.type = "SARS"
        test_data = medical_record.profile_events_by_type()
        self.assertListEqual(list(test_data.keys()), MedicalRecord.SAR_PROFILE_EVENT_TYPES)

    def test_date_range_for_records(self):
        response = self.client.get('/medicalreport/2/edit/')
        medical_record = response.context.get('medical_record')
        medical_record.instruction.date_range_to = date(2015, 10, 10)
        medical_record.instruction.date_range_from = date(1995, 10, 10)
        test_data = medical_record.consultations()
        for item in test_data:
            is_valid = True
            if medical_record.instruction.id == 2 and\
                    item.parsed_date() < medical_record.instruction.date_range_from or \
                    item.parsed_date() > medical_record.instruction.date_range_to:
                    is_valid = False
            self.assertTrue(is_valid)


class UpdateReportTest(EmisAPITestCase):
    def test_view_url(self):
        response = self.client.get('/medicalreport/1/update/')
        self.assertEqual(302, response.status_code)

    def test_view_url_by_name(self):
        response = self.client.get(
            reverse('medicalreport:update_report', args=(1,))
        )
        self.assertEqual(302, response.status_code)

    def test_view_returns_json_response_if_request_is_ajax(self):
        response = self.client.get(
            '/medicalreport/1/update/', HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(200, response.status_code)
        self.assertIsInstance(response, JsonResponse)

    def test_view_returns_404_if_instruction_does_not_exist(self):
        response = self.client.get('/medicalreport/2/update/')
        self.assertEqual(404, response.status_code)

    def test_view_redirects_to_correct_url_if_not_valid(self):
        response = self.client.post('/medicalreport/1/update/', {'event_flag': 'submit'})
        self.assertEqual(response.url, '/medicalreport/1/edit/')

    def test_view_redirects_to_correct_url_if_event_flag_is_not_submit(self):
        response = self.client.post('/medicalreport/1/update/', {'event_flag': 'draft'})
        self.assertEqual(response.url, '/instruction/view-pipeline/')

    def test_view_redirects_to_correct_url_if_event_flag_is_submit_and_is_valid(self):
        response = self.client.post('/medicalreport/1/update/', {
            'event_flag': 'submit',
            'prepared_and_signed': 'PREPARED_AND_REVIEWED',
            'prepared_by': 'test_reviewer'
        })
        self.assertEqual(response.url, '/instruction/view-pipeline/')

    def test_redirects_to_correct_url_if_no_consent_form(self):
        os.remove(self.instruction.consent_form.path)
        self.instruction.consent_form = None
        self.instruction.type = AMRA_TYPE
        self.instruction.save()
        response = self.client.post('/medicalreport/1/update/', {'event_flag': 'submit'})
        self.assertEqual(response.url, '/medicalreport/1/edit/')


class ViewReportTest(EmisAPITestCase):
    def test_view_url(self):
        response = self.client.get('/medicalreport/1/view-report/')
        self.assertEqual(200, response.status_code)

    def test_view_url_by_name(self):
        response = self.client.get(
            reverse('medicalreport:view_report', args=(1,))
        )
        self.assertEqual(200, response.status_code)

    def test_view_returns_404_if_redaction_does_not_exist(self):
        response = self.client.get('/medicalreport/2/view-report/')
        self.assertEqual(404, response.status_code)

    def test_view_returns_pdf(self):
        response = self.client.get('/medicalreport/1/view-report/')
        self.assertEqual('application/pdf', response.get('Content-Type'))


class ViewReportAttachmentTest(EmisAPITestCase):
    def test_view_url(self):
        response = self.client.get('/medicalreport/1/view-total-report/')
        self.assertEqual(200, response.status_code)

    def test_view_url_by_name(self):
        response = self.client.get(
            reverse('medicalreport:view_total_report', args=(1,))
        )
        self.assertEqual(200, response.status_code)

    def test_view_returns_404_if_redaction_does_not_exist(self):
        response = self.client.get('/medicalreport/2/view-total-report/')
        self.assertEqual(404, response.status_code)

    def test_view_returns_pdf(self):
        response = self.client.get('/medicalreport/1/view-total-report/')
        self.assertEqual('application/pdf', response.get('Content-Type'))


class ViewConsentTest(EmisAPITestCase):
    def test_view_url(self):
        response = self.client.get('/medicalreport/1/view-consent-pdf/')
        self.assertEqual(200, response.status_code)

    def test_view_url_by_name(self):
        response = self.client.get(
            reverse('medicalreport:view_consent_pdf', args=(1,))
        )
        self.assertEqual(200, response.status_code)

    def test_view_returns_404_if_redaction_does_not_exist(self):
        response = self.client.get('/medicalreport/2/view-consent-pdf/')
        self.assertEqual(404, response.status_code)

    def test_view_returns_pdf(self):
        response = self.client.get('/medicalreport/1/view-consent-pdf/')
        self.assertEqual('application/pdf', response.get('Content-Type'))


class FinalReportTest(EmisAPITestCase):
    def setUp(self):
        super().setUp()
        consent_form = SimpleUploadedFile('test_consent_form.txt', b'consent')
        self.patient_information = mommy.make(
            InstructionPatient,
            patient_first_name='Alan',
            patient_last_name='Ball',
            patient_emis_number='2985',
            patient_dob=datetime.now()
        )
        self.instruction = mommy.make(
            Instruction, pk=3, consent_form=consent_form,
            patient=self.patient, gp_user=self.gp_user,
            patient_information=self.patient_information,
            gp_practice=self.gp_practice, status=INSTRUCTION_STATUS_COMPLETE,
            mdx_consent=mdx_consent,
            medical_report=medical_report,
            medical_xml_report=medical_xml_report,
            medical_with_attachment_report=medical_with_attachment_report,
            medical_report_byte=MEDICAL_REPORT_BYTES,
            medical_with_attachment_report_byte=MEDICAL_REPORT_WITH_ATTACHMENT_BYTES,
            final_raw_medical_xml_report=RAW_MEDICAL_XML
        )
        self.reportAuth = mommy.make(
            PatientReportAuth,
            patient=self.patient,
            instruction=self.instruction,
            url='Authurl2019'
        )
        self.redaction = mommy.make(
            AmendmentsForRecord, instruction=self.instruction, pk=3,
            raw_medical_xml_aes_key=self.aes_key,
            raw_medical_xml_encrypted=RAW_MEDICAL_XML
        )

    def test_view_url(self):
        response = self.client.get('/medicalreport/3/final-report/')
        self.assertEqual(200, response.status_code)

    def test_view_url_by_name(self):
        response = self.client.get(
            reverse('medicalreport:final_report', args=(3,))
        )
        self.assertEqual(200, response.status_code)

    def test_view_uses_correct_template(self):
        response = self.client.get('/medicalreport/3/final-report/')
        self.assertTemplateUsed(response, 'medicalreport/final_report.html')

    def test_view_returns_404_if_instruction_does_not_exist(self):
        response = self.client.get('/medicalreport/5/final-report/')
        self.assertEqual(404, response.status_code)


class RedactReferencePhraseTest(TestCase):
    def setUp(self):
        super().setUp()
        ReferencePhrases.objects.create(name='father')
        gp_practice = mommy.make(
            OrganisationGeneralPractice, pk=1,
            name='GP Organisation',
            billing_address_street='99/99',
            billing_address_city='Bangkok',
            billing_address_postalcode='2510',
            gp_operating_system='OT',
            practcode='99999',
            operating_system_organisation_code=29390,
            operating_system_username='michaeljtbrooks',
            operating_system_salt_and_encrypted_password='Medidata2019',
        )
        Library.objects.create(
            gp_practice= gp_practice,
            key= 'May',
            value= 'Not',
        )

        self.value = "Mr Chatterly's father had recently been diagnosed with lymphoma"
        self.result = "Mr Chatterly's [UNSPECIFIED] had recently been diagnosed with lymphoma"
        self.relations = dict()
        relations = [relation.name for relation in ReferencePhrases.objects.all()]
        self.relations['relations'] = relations
        self.relations['word_library'] = Library.objects.filter(gp_practice=gp_practice)
        self.relations['xpath'] = [""]
        self.relations['library_history'] = None

    def test_redact_with_father(self):
        result = replace_ref_phrases(self.relations, self.value)
        self.assertEqual(self.result, result)
