from lxml import etree
import re


def xml_parse(xml_data):
    if etree.iselement(xml_data):
        return xml_data
    else:
        # Remove the default namespace definition (xmlns="http://some/namespace")
        parser = etree.XMLParser(huge_tree=True)
        xml_data = re.sub(r'\sxmlns="[^"]+"', '', xml_data, count=1)
        parsed_xml = etree.fromstring(xml_data, parser=parser)
        return parsed_xml


def redaction_elements(xml_data, remove_xpaths):
    xml = xml_parse(xml_data)
    remove_xpaths = [] if remove_xpaths is None else remove_xpaths
    for xpath in remove_xpaths:
        element = xml.xpath(xpath)
        if element:
            e = element[0]
            parent = e.getparent()
            if parent.tag == 'ConsultationElement':
                parent.getparent().remove(parent)
            else:
                parent.remove(e)
    return xml


def lxml_to_string(lxml):
    return etree.tostring(lxml,pretty_print=True)


def chronological_redactable_elements(elements):
    return sorted(elements, key=lambda x: x.parsed_date(), reverse=True)


def alphabetical_redactable_elements(elements):
    return sorted(elements, key=lambda x: x.description().lower(), reverse=False)


def normalize_data(context_data):
    """
    fill all empty places
    """
    max_elements_count = 7
    for data in context_data:
        if len(context_data[data]) > max_elements_count:
            max_elements_count = len(context_data[data])
    for data in context_data:
        if len(context_data[data]) < max_elements_count:
            length = max_elements_count - len(context_data[data])
            while length:
                context_data[data].append([])
                length = length - 1
    return context_data
