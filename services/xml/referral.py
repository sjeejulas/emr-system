from .xml_base import XMLModelBase

from typing import List


class Referral(XMLModelBase):
    XPATH = './/Referral'

    def __str__(self) -> str:
        return "Referral"

    def description(self) -> str:
        display_term = self.get_element_text('DisplayTerm')
        referral_reason = self.get_element_text('ReferralReason')

        filter_list = [t for t in [display_term, referral_reason] if t]
        if filter_list:
            return ', '.join(filter_list)
        else:
            return 'Referral'

    def provider_refid(self) -> str:
        return self.get_element_text('Provider/RefID')

    def xpaths(self) -> List[str]:
        xpath = ".//ConsultationElement[Referral/GUID='{}']".format(self.guid())
        if not self.parsed_xml.xpath(xpath):
            xpath = ".//Referral[GUID='{}']".format(self.guid())
            return [xpath]
        return [xpath]
