from .xml_base import XMLModelBase


class Allergy(XMLModelBase):
    XPATH = './/Allergy'

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
