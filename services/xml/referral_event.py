from .xml_base import XMLModelBase


class ReferralEvent(XMLModelBase):
    XPATH = ".//Event[EventType='8']"

    def description(self) -> str:
        return (
            self.get_element_text('DisplayTerm')
            or self.get_element_text('DescriptiveText')
            or 'Referral'
        )

    def provider_refid(self) -> None:
        return None
