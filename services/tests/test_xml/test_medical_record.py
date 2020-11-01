from django.test import tag

from services.tests.xml_test_case import XMLTestCase
from services.xml.medical_record import MedicalRecord
from services.xml.consultation import Consultation
from services.xml.registration import Registration
from services.xml.location import Location
from services.xml.allergy import Allergy
from services.xml.allergy_event import AllergyEvent
from services.xml.referral import Referral
from services.xml.referral_event import ReferralEvent
from services.xml.person import Person
from services.xml.problem_link_list import ProblemLinkList

from snomedct.models import SnomedConcept, ReadCode
from model_mommy import mommy


class MedicalRecordTest(XMLTestCase):
    def setUp(self):
        super().setUp(MedicalRecord.XPATH)
        self.medical_record = MedicalRecord(self.parsed_xml)
        smoking_concept = mommy.make(SnomedConcept, external_id=365981007)
        alcohol_concept = mommy.make(SnomedConcept, external_id=228273003)
        mommy.make(ReadCode, ext_read_code='SMO8', concept_id=smoking_concept)
        mommy.make(ReadCode, ext_read_code='ALC7', concept_id=alcohol_concept)

    def test_consultations_gets_all_elements_in_xml(self):
        self.assertEqual(9, len(self.medical_record.consultations()))

    def test_consultations_returns_correct_class_type(self):
        for c in self.medical_record.consultations():
            self.assertIsInstance(c, Consultation)

    def test_registration(self):
        self.assertIsInstance(self.medical_record.registration(), Registration)

    def test_acute_medications(self):
        self.assertEqual(2, len(self.medical_record.acute_medications()))

    def test_repeat_medications(self):
        self.assertEqual(2, len(self.medical_record.repeat_medications()))

    def test_referrals_gets_all_referrals(self):
        referrals = self.medical_record.referrals()
        self.assertEqual(3, len(referrals))

    def test_referrals_gets_correct_types(self):
        referrals = self.medical_record.referrals()
        self.assertIsInstance(referrals[0], Referral)
        self.assertIsInstance(referrals[2], ReferralEvent)

    def test_attachments(self):
        self.assertEqual(3, len(self.medical_record.attachments()))

    def test_all_allergies_gets_all_allergies(self):
        allergies = self.medical_record.all_allergies()
        self.assertEqual(2, len(allergies))

    def test_all_allergies_gets_correct_types(self):
        allergies = self.medical_record.all_allergies()
        self.assertIsInstance(allergies[0], Allergy)
        self.assertIsInstance(allergies[1], AllergyEvent)

    def test_people_gets_all_people(self):
        self.assertEqual(1, len(self.medical_record.people()))

    def test_people_gets_correct_type(self):
        self.assertIsInstance(self.medical_record.people()[0], Person)

    def test_locations_gets_all_locations(self):
        self.assertEqual(1, len(self.medical_record.locations()))

    def test_locations_gets_correct_type(self):
        self.assertIsInstance(self.medical_record.locations()[0], Location)

    def test_problem_linked_lists_gets_all_problem_linked_lists(self):
        self.assertEqual(7, len(self.medical_record.problem_linked_lists()))

    def test_problem_linked_lists_gets_correct_type(self):
        self.assertIsInstance(
            self.medical_record.problem_linked_lists()[0],
            ProblemLinkList
        )

    def test_height(self):
        self.assertEqual(4, len(self.medical_record.height()))

    def test_weight(self):
        self.assertEqual(4, len(self.medical_record.weight()))

    def test_bmi(self):
        self.assertEqual(4, len(self.medical_record.bmi()))

    def test_systolic_blood_pressure(self):
        self.assertEqual(1, len(self.medical_record.systolic_blood_pressure()))

    def test_diastolic_blood_pressure(self):
        self.assertEqual(1, len(self.medical_record.diastolic_blood_pressure()))

    def test_blood_test(self):
        self.assertEqual(1, len(self.medical_record.blood_test('white_blood_count')))
        self.assertEqual(1, len(self.medical_record.blood_test('hemoglobin')))

    def test_profile_event_calls_function_if_in_profile_event_type_list(self):
        pe_heights = self.medical_record.profile_event('height')
        self.assertEqual(len(self.medical_record.height()), len(pe_heights))
        for ve in pe_heights:
            self.assertTrue(ve.has_height())

    def test_profile_event_returns_empty_list_for_unrecognised_function(self):
        self.assertEqual([], self.medical_record.profile_event('non_existent'))

    def test_smoking(self):
        self.assertEqual(2, len(self.medical_record.smoking()))

    def test_alcohol(self):
        self.assertEqual(2, len(self.medical_record.alcohol()))

    def test_significant_active_problems(self):
        for sap in self.medical_record.significant_active_problems():
            self.assertTrue(sap.is_active())
            self.assertTrue(sap.is_significant())

    def test_significant_past_problems(self):
        for spp in self.medical_record.significant_past_problems():
            self.assertFalse(spp.is_active())
            self.assertTrue(spp.is_significant())
