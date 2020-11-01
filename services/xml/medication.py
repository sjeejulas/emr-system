from .xml_base import XMLModelBase
import re
from typing import List


class Medication(XMLModelBase):
    XPATH = './/Medication'
    DATE_XPATHS = ['DateLastIssue', 'AssignedDate']
    DESCRIPTION_XPATHS = ['Drug/PreparationID/Term', 'Dosage', 'QuantityRepresentation']

    def __str__(self) -> str:
        return "Medication"

    def date(self) -> str:
        for xpath in self.DATE_XPATHS:
            date_val = self.get_element_text(xpath)
            if date_val:
                return date_val
        return ''

    # todo: JT - is the existing logic even correct? Why would we add empty
    # strings/None to the list?
    def description(self) -> str:
        desc_list = []
        for index, xpath in enumerate(self.DESCRIPTION_XPATHS):
            desc = self.get_element_text(xpath)
            if index == 0 and not desc:
                desc = 'Medication'
            if desc:
                desc_list.append(desc)
        return ', '.join(desc_list)

    def issue_count(self) -> str:
        return self.get_element_text('IssueCount')

    # JT - this will raise an error if issue_count() is ''.
    # What should the default be in this case?
    def parsed_issue_count(self) -> int:
        return int(self.issue_count())

    def prescription_type(self) -> str:
        return self.get_element_text('PrescriptionType')

    def is_repeat(self) -> bool:
        result = re.match('(REPEAT|AUTOMATIC)', self.prescription_type(), re.IGNORECASE)
        if result:
            return True
        else:
            return False

    def is_acute(self) -> bool:
        result = re.match('ACUTE', self.prescription_type(), re.IGNORECASE)
        if result:
            return True
        else:
            return False

    def snomed_concepts(self) -> List[str]:
        return list(filter(None, [(
            self.get_element_text("Drug/PreparationID[MapScheme='SNOMED']/MapCode")
            or self.get_element_text("Drug/PreparationID[Scheme='EMISPREPARATION'][MapScheme='SNOMED']/MapCode")
        )]))

    def readcodes(self) -> List[str]:
        return list(filter(None, [(
            self.get_element_text("Drug/PreparationID[Scheme='READ2']/Value")
            or self.get_element_text("Drug/PreparationID[Scheme='EMISPREPARATION'][MapScheme='READ2']/MapCode")
        )]))

    def is_significant_problem(self) -> False:
        return False

    def is_profile_event(self) -> False:
        return False

    def problem_linklist_guid(self) -> str:
        return self.get_element_text("ProblemLinkList/Link/Target/GUID")


