from services.tests.xml_test_case import XMLTestCase

from services.xml.xml_utils import (
    xml_parse, redaction_elements, chronological_redactable_elements,
    alphabetical_redactable_elements
)
from services.xml.medication import Medication


class XMLUtilsTest(XMLTestCase):
    def setUp(self):
        super().setUp()
        medication_elements = self.parsed_xml.xpath(Medication.XPATH)
        self.medications = [Medication(e) for e in medication_elements]
        presort_guids = [m.guid() for m in self.medications]
        self.assertListEqual(
            ['445798', '575848', '858585', '48499'],
            presort_guids
        )

    def test_xml_parse_returns_element_if_input_is_element(self):
        self.assertEqual(xml_parse(self.parsed_xml), self.parsed_xml)

    def test_redaction_elements(self):
        self.assertEqual(4, len(self.parsed_xml.xpath(Medication.XPATH)))
        new_xml = redaction_elements(
            self.parsed_xml, self.medications[0].xpaths())
        self.assertEqual(3, len(new_xml.xpath(Medication.XPATH)))

    def test_chronological_redactable_elements(self):
        sorted_medications = chronological_redactable_elements(self.medications)
        postsort_guids = [m.guid() for m in sorted_medications]
        self.assertListEqual(
            ['575848', '858585', '48499', '445798'],
            postsort_guids
        )

    def test_alphabetical_redactable_elements(self):
        sorted_medications = alphabetical_redactable_elements(self.medications)
        postsort_guids = [m.guid() for m in sorted_medications]
        self.assertListEqual(
            ['48499', '445798', '858585', '575848'],
            postsort_guids
        )
