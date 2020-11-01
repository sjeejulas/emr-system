from .xml_base import XMLBase

from typing import List


class Location(XMLBase):
    ADDRESS_XPATHS = ['HouseNameFlat', 'Street', 'Village', 'Town', 'County', 'PostCode']
    XPATH = './/Location'

    def address_lines(self) -> List[str]:
        address_values = []
        for xpath in self.ADDRESS_XPATHS:
            value = self.parsed_xml.find("Address/{}".format(xpath))
            if value is not None:
                address_values.append(value.text)

        location_name = list(filter(None, [self.location_name()]))
        return location_name + address_values

    def location_name(self) -> str:
        return self.get_element_text('LocationName')

    def ref_id(self) -> str:
        return self.get_element_text('RefID')
