from .registration import Registration
from .xml_base import XMLBase

from typing import List


class PatientList(XMLBase):
    XPATH = './/Patient'

    def patients(self) -> List[Registration]:
        patients_element = self.parsed_xml.findall(self.XPATH)
        patients = [Registration(patient) for patient in patients_element]
        return patients
