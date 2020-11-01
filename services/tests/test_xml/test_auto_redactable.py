from django.test import tag

from services.tests.xml_test_case import XMLTestCase
from services.xml.auto_redactable import (
    years_ago, auto_redact_by_conditions, auto_redact_consultations, auto_redact_by_link_conditions,
    auto_redact_medications, auto_redact_referrals, auto_redact_attachments,
    auto_redact_profile_events
)
from services.xml.attachment import Attachment
from services.xml.consultation import Consultation
from services.xml.medication import Medication
from services.xml.referral import Referral
from services.xml.value_event import ValueEvent
from services.xml.medical_record import MedicalRecord

from instructions.models import Instruction, InstructionConditionsOfInterest
from instructions import model_choices
from snomedct.models import SnomedConcept, ReadCode

from model_mommy import mommy

from datetime import date


class AutoRedactableTest(XMLTestCase):
    def setUp(self):
        super().setUp()
        medication_elements = self.parsed_xml.xpath(Medication.XPATH)
        self.medical_record = MedicalRecord(self.parsed_xml)
        self.medications = [Medication(e) for e in medication_elements]
        self.instruction_with_range = mommy.make(
                Instruction,
                date_range_from=date(2016, 1, 1),
                date_range_to=date(2016, 12, 10)
        )
        self.instruction_with_sars = mommy.make(Instruction, type='SARS')
        self.instruction = mommy.make(Instruction, type='AMRA')
        snomed_ct_1 = mommy.make(
            SnomedConcept, external_id=90332006)
        snomed_ct_2 = mommy.make(
            SnomedConcept, external_id=1331000000103)
        mommy.make(ReadCode, ext_read_code='1371.', concept_id=snomed_ct_1)
        mommy.make(ReadCode, ext_read_code='9D11.', concept_id=snomed_ct_2)
        mommy.make(
            InstructionConditionsOfInterest, instruction=self.instruction,
            snomedct=snomed_ct_1
        )
        mommy.make(
            InstructionConditionsOfInterest, instruction=self.instruction,
            snomedct=snomed_ct_2
        )

    def test_years_ago(self):
        test_date_1 = date(2016, 2, 29)
        test_date_2 = date(2018, 10, 1)
        test_date_3 = date(2017, 2, 28)
        expected_date_1 = date(2015, 2, 28)
        expected_date_2 = date(2017, 10, 1)
        expected_date_3 = date(2016, 2, 28)
        self.assertEqual(expected_date_1, years_ago(1, test_date_1))
        self.assertEqual(expected_date_2, years_ago(1, test_date_2))
        self.assertEqual(expected_date_3, years_ago(1, test_date_3))

    def test_auto_redact_by_conditions(self):
        self.assertEqual(4, len(self.medications))
        self.assertEqual(
            0,
            len(auto_redact_by_link_conditions(self.medications, self.instruction, self.medical_record))
        )

    def test_auto_redact_by_date(self):
        self.test_auto_redact_referrals()

    def test_auto_redact_consultations(self):
        consultation_elements = self.parsed_xml.xpath(Consultation.XPATH)
        consultations = [Consultation(e) for e in consultation_elements]
        self.assertEqual(9, len(consultations))
        test_date = date(2018, 1, 1)
        self.assertEqual(
            2,
            len(auto_redact_consultations(
                consultations, self.instruction, test_date))
        )

    def test_auto_redact_consultations_with_sars(self):
        consultation_elements = self.parsed_xml.xpath(Consultation.XPATH)
        consultations = [Consultation(e) for e in consultation_elements]
        self.assertEqual(9, len(consultations))
        test_date = date(2018, 1, 1)
        self.assertEqual(
            9,
            len(auto_redact_consultations(
                consultations, self.instruction_with_sars, test_date))
        )

    def test_auto_redact_consultations_with_range(self):
        consultation_elements = self.parsed_xml.xpath(Consultation.XPATH)
        consultations = [Consultation(e) for e in consultation_elements]
        self.assertEqual(9, len(consultations))
        test_date = date(2018, 1, 1)
        self.assertEqual(
            1,
            len(auto_redact_consultations(
                consultations, self.instruction_with_range, test_date))
        )

    def test_auto_redact_medications(self):
        test_date = date(2018, 1, 1)
        self.assertEqual(4, len(self.medications))
        self.assertEqual(
            0,
            len(auto_redact_medications(self.medications, self.instruction, self.medical_record, current_date=test_date))
        )

    def test_auto_redact_medications_with_sars(self):
        test_date = date(2018, 1, 1)
        self.assertEqual(4, len(self.medications))
        self.assertEqual(
            4,
            len(auto_redact_medications(self.medications, self.instruction_with_sars, test_date))
        )

    def test_auto_redact_medications_with_range(self):
        test_date = date(2018, 1, 1)
        self.assertEqual(4, len(self.medications))
        self.assertEqual(
            2,
            len(auto_redact_medications(self.medications, self.instruction_with_range, test_date))
        )

    def test_auto_redact_referrals(self):
        referral_elements = self.parsed_xml.xpath(Referral.XPATH)
        referrals = [Referral(e) for e in referral_elements]
        test_date = date(2018, 1, 1)
        self.assertEqual(2, len(referrals))
        self.assertEqual(
            0,
            len(auto_redact_referrals(referrals, self.instruction, test_date))
        )

    def test_auto_redact_referrals_with_sars(self):
        referral_elements = self.parsed_xml.xpath(Referral.XPATH)
        referrals = [Referral(e) for e in referral_elements]
        test_date = date(2018, 1, 1)
        self.assertEqual(2, len(referrals))
        self.assertEqual(
            2,
            len(auto_redact_referrals(referrals, self.instruction_with_sars, test_date))
        )

    def test_auto_redact_referrals_with_range(self):
        referral_elements = self.parsed_xml.xpath(Referral.XPATH)
        referrals = [Referral(e) for e in referral_elements]
        test_date = date(2018, 1, 1)
        self.assertEqual(2, len(referrals))
        self.assertEqual(
            1,
            len(auto_redact_referrals(referrals, self.instruction_with_range, test_date))
        )

    def test_auto_redact_attachments(self):
        attachment_elements = self.parsed_xml.xpath(Attachment.XPATH)
        attachments = [Attachment(e) for e in attachment_elements]
        test_date = date(2019, 1, 1)
        self.assertEqual(3, len(attachments))
        self.assertEqual(
            2,
            len(auto_redact_attachments(attachments, self.instruction, test_date))
        )

    def test_auto_redact_attachments(self):
        attachment_elements = self.parsed_xml.xpath(Attachment.XPATH)
        attachments = [Attachment(e) for e in attachment_elements]
        test_date = date(2019, 1, 1)
        self.assertEqual(3, len(attachments))
        self.assertEqual(
            3,
            len(auto_redact_attachments(attachments, self.instruction_with_sars, test_date))
        )

    def test_auto_redact_attachments_with_range(self):
        attachment_elements = self.parsed_xml.xpath(Attachment.XPATH)
        attachments = [Attachment(e) for e in attachment_elements]
        test_date = date(2019, 1, 1)
        self.assertEqual(3, len(attachments))
        self.assertEqual(
            1,
            len(auto_redact_attachments(attachments, self.instruction_with_range, test_date))
        )

    def test_auto_redact_profile_events(self):
        value_event_elements = self.parsed_xml.xpath(ValueEvent.XPATH)
        value_events = [ValueEvent(e) for e in value_event_elements]
        test_date = date(2020, 1, 1)
        self.assertEqual(21, len(value_events))
        self.assertEqual(
            12,
            len(auto_redact_profile_events(value_events, self.instruction, test_date))
        )

    def test_auto_redact_profile_events_with_sars(self):
        value_event_elements = self.parsed_xml.xpath(ValueEvent.XPATH)
        value_events = [ValueEvent(e) for e in value_event_elements]
        test_date = date(2020, 1, 1)
        self.assertEqual(21, len(value_events))
        self.assertEqual(
            21,
            len(auto_redact_profile_events(value_events, self.instruction_with_sars, test_date))
        )

    def test_auto_redact_profile_events_with_range(self):
        value_event_elements = self.parsed_xml.xpath(ValueEvent.XPATH)
        value_events = [ValueEvent(e) for e in value_event_elements]
        test_date = date(2020, 1, 1)
        self.assertEqual(21, len(value_events))
        self.assertEqual(
            0,
            len(auto_redact_profile_events(value_events, self.instruction_with_range, test_date))
        )
