from . import xml_utils
from datetime import datetime, date as date_type
from typing import List, Optional


class XMLBase:
    def __init__(self, xml_data):
        self.parsed_xml = xml_utils.xml_parse(xml_data)

    def get_element_text(self, element_name: str) -> str:
        value = self.parsed_xml.find(element_name)
        if value is None:
            return ''
        if value.text is None:
            return ''
        return value.text.strip() or ''


class XMLModelBase(XMLBase):
    def xpaths(self) -> List[str]:
        xpath = ".//{}[GUID='{}']".format(self.parsed_xml.tag, self.guid())
        return [xpath]

    def guid(self) -> str:
        return self.get_element_text('GUID')

    def date(self) -> str:
        return self.get_element_text('AssignedDate')

    def parsed_date(self) -> Optional[date_type]:
        date_str = self.date()
        if not date_str:
            return None
        return datetime.strptime(date_str, "%d/%m/%Y").date()

    def readcodes(self) -> List[str]:
        codes = self.parsed_xml.findall(".//Code[Scheme='READ2']/Value")
        return [code.text for code in codes]

    def snomed_concepts(self):
        snomeds = self.parsed_xml.findall(".//Code[MapScheme='SNOMED']/MapCode")
        return [snomed.text for snomed in snomeds]

    def map_code(self) -> List[str]:
        map_codes = self.parsed_xml.findall(".//Code/MapCode")
        return [map_code.text for map_code in map_codes]
