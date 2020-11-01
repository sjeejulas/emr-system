from .xml_base import XMLBase
import base64
import re


class Base64Attachment(XMLBase):
    XPATH = './/Base64Attachment'

    def filedata(self) -> str:
        return self.get_element_text('filedata')

    def data(self) -> bytes:
        file_data = self.filedata()
        if not file_data:
            return None
        return base64.b64decode(file_data)

    def filename(self) -> str:
        return self.get_element_text('filename')

    def file_basename(self) -> str:
        filename = self.filename()
        if not filename:
            return None
        return re.findall(r'[^\\]+\Z', filename)[0]
