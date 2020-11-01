from .xml_base import XMLModelBase
from datetime import datetime
from typing import List, Optional


class Problem(XMLModelBase):
    XPATH = './/*[Problem]'

    def is_active(self) -> Optional[bool]:
        value = self.get_element_text('Problem/ProblemStatus')
        if not value:
            return None
        return value == '1'

    def is_past(self) -> Optional[bool]:
        value = self.get_element_text('Problem/ProblemStatus')
        if not value:
            return None
        return value == '0'

    def is_significant(self) -> Optional[bool]:
        value = self.get_element_text('Problem/Significance')
        if not value:
            return None
        return value == '1'

    def is_minor(self) -> Optional[bool]:
        value = self.get_element_text('Problem/Significance')
        if not value:
            return None
        return value == '2'

    def end_date(self) -> str:
        if self.is_active():
            return ''
        return self.get_element_text('Problem/EndDate')

    def parsed_end_date(self) -> Optional[datetime.date]:
        end_date = self.end_date()
        if not end_date:
            return None
        return datetime.strptime(end_date, "%d/%m/%Y").date()

    def description(self) -> str:
        return (
            self.get_element_text('DisplayTerm')
            or self.get_element_text('Code/Term')
        )

    def xpaths(self) -> List[str]:
        xpaths = self.__parent_xpath() + self.__problem_xpath()
        for xpath in xpaths:
            if 'Event' in xpath:
                return [xpath]
        return []

    # private
    # JT - this method looks pretty brittle.
    def __parent_xpath(self) -> List[str]:
        parent = self.parsed_xml.getparent().getparent().getparent()
        if parent is not None:
            xpath = ".//{}[GUID='{}']".format(parent.tag, parent.find('GUID').text)
            return [xpath]
        else:
            return []

    def __problem_xpath(self):
        return super().xpaths()
