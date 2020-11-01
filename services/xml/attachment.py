from .xml_base import XMLModelBase

from typing import List


class Attachment(XMLModelBase):
    XPATH = './/Attachment'
    DESCRIPTION_XPATHS = ['DescriptiveText', 'DisplayTerm', 'Code/Term']
    TITLE_XPATHS = 'Title'

    def __str__(self) -> str:
        return "Attachment"

    def description(self) -> str:
        for xpath in self.DESCRIPTION_XPATHS:
            desc = self.parsed_xml.find(xpath)
            if desc is not None:
                return desc.text
        return 'Attachment'

    def title(self) -> str:
        title = self.parsed_xml.find(self.TITLE_XPATHS)
        if title is not None:
            return title.text
        return 'Title'

    def dds_identifier(self) -> str:
        return self.get_element_text('DDSIdentifier')

    def to_param(self) -> str:
        return self.dds_identifier()

    # JT What about attachments inside an AttachmentList element? This xpath
    # will not be valid for those.
    def xpaths(self) -> List[str]:
        xpath = ".//Attachment[GUID='{}']".format(self.guid())
        return [xpath]
