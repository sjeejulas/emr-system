from .xml_base import XMLModelBase
from typing import List


class RelationElement(XMLModelBase):
    XPATH = './/Qualifier'

    def __str__(self) -> str:
        return "RelationElement"

    def description(self) -> str:
        value = self.get_element_text('QualifierItemID/Term')
        return value


class Relation(XMLModelBase):
    XPATH = ".//Event[EventType='12']"

    def __str__(self) -> str:
        return "Relation"

    def relation_elements(self) -> List[RelationElement]:
        elements = self.parsed_xml.findall(RelationElement.XPATH)
        result_list = [RelationElement(element) for element in elements]
        return result_list
