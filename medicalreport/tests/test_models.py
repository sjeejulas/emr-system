from django.test import TestCase

from model_mommy import mommy

from medicalreport.models import (
    AmendmentsForRecord, AdditionalMedicationRecords, AdditionalAllergies
)
from instructions.models import Instruction, InstructionPatient
from instructions import model_choices
from accounts.models import User, Patient, GeneralPracticeUser


class AmendmentsForRecordTest(TestCase):
    def setUp(self):
        patient = mommy.make(Patient, emis_number='12345')
        self.patient_information = mommy.make(InstructionPatient, patient_emis_number='12345')
        self.instruction_1 = mommy.make(
            Instruction, status=model_choices.INSTRUCTION_STATUS_COMPLETE,
            patient=patient, patient_information=self.patient_information
        )
        self.instruction_2 = mommy.make(Instruction, status=model_choices.INSTRUCTION_STATUS_PROGRESS)
        user = mommy.make(User, first_name='pete', last_name='john')
        self.gp_user = mommy.make(GeneralPracticeUser, user=user)
        self.amendments_1 = mommy.make(
            AmendmentsForRecord, instruction=self.instruction_1,
            prepared_by=self.gp_user, review_by=user
        )
        self.amendments_2 = mommy.make(
            AmendmentsForRecord, instruction=self.instruction_2,
            redacted_xpaths=None
        )
        mommy.make(
            AdditionalMedicationRecords, repeat=False,
            amendments_for_record=self.amendments_1
        )
        mommy.make(
            AdditionalMedicationRecords, repeat=True,
            amendments_for_record=self.amendments_1
        )
        mommy.make(AdditionalAllergies, amendments_for_record=self.amendments_1)

    def test_patient_emis_number(self):
        self.assertEqual('12345', self.amendments_1.patient_emis_number)

    def test_get_gp_name_when_instruction_status_is_not_complete(self):
        self.assertEqual('', self.amendments_2.get_gp_name())

    def test_get_gp_name_when_instruction_status_is_complete(self):
        self.assertEqual(self.gp_user, self.amendments_1.get_gp_name())

    def test_get_gp_name_when_prepared_by_is_blank(self):
        self.amendments_1.prepared_by = None
        self.assertEqual('', self.amendments_1.get_gp_name())

    def test_get_gp_name_when_prepared_by_and_reviewed_by_are_blank(self):
        self.amendments_1.prepared_by = None
        self.amendments_1.review_by = None
        self.assertEqual('', self.amendments_1.get_gp_name())

    def test_additional_acute_medications(self):
        self.assertEqual(1, self.amendments_1.additional_acute_medications().count())

    def test_additional_repeat_medications(self):
        self.assertEqual(1, self.amendments_1.additional_repeat_medications().count())

    def test_additional_allergies(self):
        self.assertEqual(1, self.amendments_1.additional_allergies().count())

    def test_redacted_returns_false_if_redacted_xpaths_is_none(self):
        self.assertFalse(self.amendments_2.redacted(''))

    def test_redacted_returns_false_if_not_all_xpaths_are_in_redacted_xpaths(self):
        self.amendments_1.redacted_xpaths = ['a', 'b', 'c']
        self.amendments_1.save()
        self.assertFalse(self.amendments_1.redacted(['a', 'b', 'f']))

    def test_redacted_returns_true_if_all_xpaths_are_in_redacted_xpaths(self):
        self.amendments_1.redacted_xpaths = ['a', 'b', 'c']
        self.amendments_1.save()
        self.assertTrue(self.amendments_1.redacted(['a', 'b']))
