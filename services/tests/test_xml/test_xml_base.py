from services.tests.xml_test_case import XMLTestCase
from services.xml.xml_base import XMLBase
from services.xml.medication import Medication

from datetime import date


class XMLBaseTest(XMLTestCase):
    def setUp(self):
        super().setUp()
        self.address = XMLBase(self.parsed_xml.find('.//Registration/Address'))

    def test_get_element_text(self):
        self.assertEqual(
            'Four Lane Ends',
            self.address.get_element_text('Village')
        )

    def test_get_element_text_returns_empty_string_if_element_not_present(self):
        self.assertEqual('', self.address.get_element_text('Gate'))


class XMLModelBaseTest(XMLTestCase):
    def setUp(self):
        super().setUp(Medication.XPATH)
        self.medications = [Medication(e) for e in self.elements]

    def test_xpaths(self):
        self.assertListEqual(
            [".//Medication[GUID='445798']"],
            self.medications[0].xpaths()
        )

    def test_guid(self):
        self.assertEqual('445798', self.medications[0].guid())

    def test_date(self):
        self.assertEqual('20/08/2002', self.medications[0].date())

    def test_parsed_date(self):
        self.assertEqual(date(2002, 8, 20), self.medications[0].parsed_date())

    def test_readcodes(self):
        self.assertListEqual(['NEWCODE'], self.medications[2].readcodes())

    def test_snomed_concepts(self):
        self.assertListEqual(
            ['90332006'],
            self.medications[1].snomed_concepts()
        )
