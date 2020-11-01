from .xml_base import XMLModelBase


class AllergyEvent(XMLModelBase):
    XPATH = ".//Event[EventType='11']"

    def description(self) -> str:
        return (
            self.get_element_text('DisplayTerm')
            or self.get_element_text('DescriptiveText')
        )
