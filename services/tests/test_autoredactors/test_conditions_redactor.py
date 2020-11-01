from services.tests.xml_test_case import XMLTestCase

from services.autoredactors.conditions_redactor import ConditionsRedactor

from services.xml.medication import Medication


class ConditionsRedactorTest(XMLTestCase):
    def setUp(self):
        super().setUp(Medication.XPATH)
        self.medications = [Medication(e) for e in self.elements]
        self.medication_no_codes = self.medications[0]
        self.medication_snomed = self.medications[1]
        self.medication_read2 = self.medications[2]
        self.concepts = [90332006]
        self.readcodes = ['NEWCODE']

    def test_is_redact_returns_false_when_redactor_has_no_codes(self):
        redactor = ConditionsRedactor()
        for m in self.medications:
            self.assertFalse(redactor.is_redact(m))

    def test_is_redact_returns_true_when_redactor_has_codes_and_model_has_no_codes(self):
        redactor = ConditionsRedactor(self.concepts, self.readcodes)
        self.assertTrue(redactor.is_redact(self.medication_no_codes))

    def test_is_redact_returns_true_when_there_are_no_snomed_matches(self):
        redactor = ConditionsRedactor([1234], self.readcodes)
        self.assertTrue(redactor.is_redact(self.medication_snomed))

    def test_is_redact_returns_true_when_there_are_no_readcode_matches(self):
        redactor = ConditionsRedactor(self.concepts, ['OLDCODE'])
        self.assertTrue(redactor.is_redact(self.medication_read2))

    def test_is_redact_returns_false_when_snomeds_match(self):
        redactor = ConditionsRedactor(self.concepts, [])
        self.assertFalse(redactor.is_redact(self.medication_snomed))

    def test_is_redact_returns_false_when_readcodes_match(self):
        redactor = ConditionsRedactor([], self.readcodes)
        self.assertFalse(redactor.is_redact(self.medication_read2))
