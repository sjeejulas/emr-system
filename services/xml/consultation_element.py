from .xml_base import XMLModelBase
from .value_event import ValueEvent
from .referral_event import ReferralEvent
from .allergy_event import AllergyEvent
from .attachment import Attachment
from .medication import Medication
from .referral import Referral
from .allergy import Allergy
from .problem import Problem

from typing import Optional


class GenericContent(XMLModelBase):
    XPATH = '*[last()]'

    def __str__(self) -> str:
        return "GenericContent"

    def description(self) -> str:
        term = (
            self.get_element_text('DisplayTerm')
            or self.get_element_text('Code/Term')
        )
        descriptive_text = self.get_element_text('DescriptiveText')

        terms = [t for t in [term, descriptive_text] if t]
        if terms:
            return ', '.join(terms)
        else:
            return ''


class ConsultationElement(XMLModelBase):
    XPATH = './/ConsultationElement'
    CONTENT_CLASSES = [
        ValueEvent,
        ReferralEvent,
        AllergyEvent,
        Attachment,
        Medication,
        Referral,
        Allergy,
    ]

    def header(self) -> str:
        return self.get_element_text('Header/Term')

    def display_order(self) -> int:
        display_order = self.get_element_text('DisplayOrder')
        if not display_order:
            return -1
        return int(display_order)

    def content(self) -> XMLModelBase:
        for klass in self.CONTENT_CLASSES:
            element = self.parsed_xml.find(klass.XPATH)
            if element is not None:
                return klass(element)

        generic_content = self.parsed_xml.xpath(GenericContent.XPATH)[0]
        return GenericContent(generic_content)

    def problem(self) -> Optional[Problem]:
        problem = self.content().parsed_xml.xpath('.//Problem')
        if not problem:
            return None
        return Problem(self.content().parsed_xml)

    def is_significant_problem(self) -> bool:
        problem = self.problem()
        if problem is None:
            return False
        return problem.is_significant()

    def xpaths(self):
        xpath = ".//{}[GUID='{}']".format(self.content().parsed_xml.tag, self.content().guid())
        return [xpath]
