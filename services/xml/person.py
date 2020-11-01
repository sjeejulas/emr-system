from .xml_base import XMLBase


class Person(XMLBase):
    XPATH = './/Person'
    NAME_XPATHS = ['FirstNames', 'LastName']

    def full_name(self) -> str:
        result = self.name()
        if self.category_description() is not '':
            result = '{} ({})'.format(result, self.category_description())
        return result

    def category_description(self) -> str:
        return self.get_element_text('Category/Description')

    def name(self) -> str:
        result = []
        for xpath in self.NAME_XPATHS:
            value = self.parsed_xml.find(xpath)
            if hasattr(value, 'text') and value.text is not None:
                result.append(value.text)
        return ' '.join(result)

    def ref_id(self) -> str:
        return self.get_element_text('RefID')
