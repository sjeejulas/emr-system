from services.tests.xml_test_case import XMLTestCase

from services.xml.medication import Medication


class MedicationTest(XMLTestCase):
    def setUp(self):
        super().setUp(Medication.XPATH)
        self.medications = [Medication(e) for e in self.elements]

    def test_string_representation(self):
        self.assertEqual('Medication', str(self.medications[0]))

    def test_date_with_assigned_date(self):
        self.assertEqual('20/08/2002', self.medications[0].date())

    def test_date_with_date_last_issue(self):
        self.assertEqual('03/09/2016', self.medications[2].date())

    def test_description(self):
        self.assertEqual(
            'Liquid paraffin light 63.4% bath additive, Add One To Three '
            'Capfuls To Bath Water, 250 ml',
            self.medications[2].description()
        )

    def test_issue_count(self):
        self.assertEqual('1', self.medications[0].issue_count())

    def test_parsed_issue_count(self):
        self.assertEqual(1, self.medications[0].parsed_issue_count())

    def test_prescription_type(self):
        self.assertEqual('ACUTE', self.medications[0].prescription_type())
        self.assertEqual('REPEAT', self.medications[2].prescription_type())

    def test_is_repeat(self):
        self.assertFalse(self.medications[0].is_repeat())
        self.assertTrue(self.medications[2].is_repeat())

    def test_is_acute(self):
        self.assertTrue(self.medications[0].is_acute())
        self.assertFalse(self.medications[2].is_acute())

    def test_snomed_concepts(self):
        self.assertListEqual(
            ['90332006'],
            self.medications[1].snomed_concepts()
        )

    def test_snomed_concepts_returns_empty_list_if_no_snomed_concepts_present(self):
        self.assertEqual([], self.medications[0].snomed_concepts())

    def test_readcodes(self):
        self.assertListEqual(['NEWCODE'], self.medications[2].readcodes())

    def test_readcodes_returns_empty_list_if_no_readcodes_present(self):
        self.assertEqual([], self.medications[0].readcodes())

    def test_is_significant_problem_always_returns_false(self):
        for m in self.medications:
            self.assertFalse(m.is_significant_problem())

    def test_is_profile_event_always_returns_false(self):
        for m in self.medications:
            self.assertFalse(m.is_profile_event())
