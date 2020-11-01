from services.tests.xml_test_case import XMLTestCase

from services.xml.consultation import Consultation


class ConsultationTest(XMLTestCase):
    def setUp(self):
        super().setUp(Consultation.XPATH)
        self.consultations = [Consultation(e) for e in self.elements]

    def test_date(self):
        self.assertEqual('01/02/2018', self.consultations[0].date())

    def test_consultation_elements(self):
        self.assertEqual(11, len(self.consultations[0].consultation_elements()))

    def test_snomed_concepts(self):
        self.assertListEqual(['38082009'], self.consultations[0].snomed_concepts())

    def test_readcodes(self):
        self.assertListEqual(
            [
                '1371.', '1361.', '246A.', '2469.', '42H7.', '42P..', '42A..',
                '428..', '42J..', '42M..'
            ],
            self.consultations[0].readcodes()
        )

    def test_original_author_refid(self):
        self.assertEqual('678', self.consultations[7].original_author_refid())

    def test_is_significant_problem(self):
        self.assertFalse(self.consultations[0].is_significant_problem())
        self.assertTrue(self.consultations[2].is_significant_problem())

    def test_is_profile_event(self):
        self.assertFalse(self.consultations[1].is_profile_event())
        self.assertTrue(self.consultations[0].is_profile_event())

    def test_is_sick_note_returns_false_when_relevant_codes_not_present(self):
        self.assertFalse(self.consultations[0].is_sick_note())

    def test_is_sick_note_from_readcodes(self):
        self.assertTrue(self.consultations[7].is_sick_note())

    def test_is_sick_note_from_snomed_concepts(self):
        self.assertTrue(self.consultations[8].is_sick_note())
