from .xml_base import XMLModelBase

from typing import List


class ProblemLinkList(XMLModelBase):
    XPATH = './/*[ProblemLinkList]'

    def target_guids(self) -> List[str]:
        elements = self.parsed_xml.findall('ProblemLinkList/Link/Target/GUID')
        result_list = [element.text for element in elements]
        return result_list

    def xpaths(self) -> List[str]:
        xpaths = self.__parent_xpath() + self.__problem_xpath()
        for xpath in xpaths:
            if 'Event' in xpath:
                return [xpath]
        return []

    # private
    def __parent_xpath(self) -> List[str]:
        parent = self.parsed_xml.getparent().getparent().getparent()
        if parent is not None:
            xpath = ".//{}[GUID='{}']".format(parent.tag, parent.find('GUID').text)
            return [xpath]
        else:
            return []

    def __problem_xpath(self) -> List[str]:
        return super().xpaths()
