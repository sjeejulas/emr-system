from datetime import datetime
from .xml_base import XMLBase

from typing import List


class Registration(XMLBase):
    XPATH = './/Registration'
    REGISTRATION_STATUS_XPATH = './/RegistrationStatus'
    NAME_XPATHS = ['Title', 'FirstNames', 'FamilyName']
    ADDRESS_XPATHS = ['HouseNameFlat', 'Street', 'Village', 'Town', 'County', 'PostCode']

    def date_of_birth(self) -> str:
        return self.get_element_text('DateOfBirth')

    def date_of_registration(self) -> str:
        value = self.parsed_xml.find('CurrentStatus/{}'.format('StatusDate'))
        if value is None:
            return ''
        if value.text is None:
            return ''
        return value.text.strip() or ''

    def parsed_date_of_birth(self) -> datetime.date:
        date_of_birth = self.date_of_birth()
        if not date_of_birth:
            return None
        return datetime.strptime(date_of_birth, "%d/%m/%Y").date()

    def parsed_registration_status_date(self) -> datetime.date:
        registration_date = self.date_of_registration()
        if not registration_date:
            return None
        return datetime.strptime(registration_date, "%d/%m/%Y").date()

    def sex(self) -> str:
        return self.get_element_text('Sex')

    def full_name(self) -> str:
        name = []
        for xpath in self.NAME_XPATHS:
            value = self.parsed_xml.find(xpath)
            if value is not None:
                name.append(value.text)
        return ' '.join(name)

    def nhs_number(self) -> str:
        return self.get_element_text('NhsNumber')

    def address_lines(self) -> List[str]:
        address = []
        for xpath in self.ADDRESS_XPATHS:
            value = self.parsed_xml.find('Address/{}'.format(xpath))
            if value is not None and value.text is not None:
                address.append(value.text)
        return address

    def ref_id(self) -> str:
        return self.get_element_text('RefID')

    def mobile_number(self) -> str:
        return self.get_element_text('Mobile')

    def home_telephone(self) -> str:
        return self.get_element_text('HomeTelephone')

    def email(self) -> str:
        return self.get_element_text('Email')
