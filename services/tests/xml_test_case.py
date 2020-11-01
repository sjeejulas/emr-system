from django.test import TestCase

from services.xml.xml_utils import xml_parse


class XMLTestCase(TestCase):
    def setUp(self, xpath=''):
        with open('services/tests/test_data/medical_record.xml') as xml_file:
            self.parsed_xml = xml_parse(
                ''.join(xml_file.read()).replace('\n', '')
            )
        if xpath:
            self.elements = self.parsed_xml.xpath(xpath)
