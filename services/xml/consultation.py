from .xml_base import XMLModelBase
from .consultation_element import ConsultationElement
from .value_event import ValueEvent

from typing import List


class Consultation(XMLModelBase):
    XPATH = './/Consultation'

    def consultation_elements(self) -> List[ConsultationElement]:
        elements = self.parsed_xml.findall(ConsultationElement.XPATH)
        result_list = [ConsultationElement(element) for element in elements]
        return result_list

    def snomed_concepts(self) -> List[str]:
        result_list = []
        for element in self.consultation_elements():
            result_list += element.content().snomed_concepts()
        return result_list

    def readcodes(self) -> List[str]:
        result_list = []
        for element in self.consultation_elements():
            result_list += element.content().readcodes()
        return result_list

    def original_author_refid(self) -> str:
        return self.get_element_text('OriginalAuthor/User/RefID')

    def is_significant_problem(self) -> bool:
        return any(element.is_significant_problem() for element in self.consultation_elements())

    def is_profile_event(self) -> bool:
        return any(element is not None for element in self.parsed_xml.xpath(ValueEvent.XPATH))

    def is_sick_note(self) -> bool:
        sick_note_readcodes = ['9D11.', '9D15.']
        sick_note_snomedcodes = ['1331000000103', '751731000000106']
        if any(code in self.readcodes() for code in sick_note_readcodes):
            return True
        if any(code in self.snomed_concepts() for code in sick_note_snomedcodes):
            return True
        return False
