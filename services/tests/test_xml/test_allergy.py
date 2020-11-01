from services.tests.xml_test_case import XMLTestCase

from services.xml.allergy import Allergy


class AllergyTest(XMLTestCase):
    def setUp(self):
        super().setUp(Allergy.XPATH)
        self.allergies = [Allergy(e) for e in self.elements]

    def test_description(self):
        self.assertEqual(
            'Adverse reaction to Co-Trimoxazole, Rash',
            self.allergies[0].description()
        )
