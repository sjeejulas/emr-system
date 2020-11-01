from django.conf import settings
from .xml_base import XMLModelBase

import yaml
import os
from typing import List


class ValueEvent(XMLModelBase):
    XPATH = ".//Event[EventType='5']"
    SPECIFIED_BLOOD_CODES = None

    def __str__(self) -> str:
        return "ValueEvent"

    def description(self) -> str:
        value = self.get_element_text('NumericValue/Value')
        unit = self.get_element_text('NumericValue/Units')
        return "{} {}".format(value, unit)

    def has_bmi(self) -> bool:
        readcodes = self.readcodes()
        if readcodes:
            if '22K..' in readcodes:
                return True
            else:
                return False
        else:
            if '60621009' in self.snomed_concepts():
                return True
            else:
                return False

    def has_weight(self) -> bool:
        readcodes = self.readcodes()
        if readcodes:
            if '22A..' in readcodes:
                return True
            else:
                return False
        else:
            if '162763007' in self.snomed_concepts():
                return True
            else:
                return False

    def has_height(self) -> bool:
        readcodes = self.readcodes()
        if readcodes:
            if '229..' in readcodes:
                return True
            else:
                return False
        else:
            if '162755006' in self.snomed_concepts():
                return True
            else:
                return False

    def has_systolic_blood_pressure(self) -> bool:
        readcodes = self.readcodes()
        if readcodes:
            if '2469.' in readcodes:
                return True
            else:
                return False
        else:
            if '163030003' in self.snomed_concepts():
                return True
            else:
                return False

    def has_diastolic_blood_pressure(self) -> bool:
        readcodes = self.readcodes()
        if readcodes:
            if '246A.' in readcodes:
                return True
            else:
                return False
        else:
            if '163031004' in self.snomed_concepts():
                return True
            else:
                return False

    def has_spirometry(self) -> bool:
            if '59328004' in self.snomed_concepts() or '50834005' in self.snomed_concepts():
                return True
            else:
                return False

    def has_peak_flow(self) -> bool:
            if '18491006' in self.snomed_concepts() or '313192007' in self.snomed_concepts() or\
                    '178271000000100' in self.snomed_concepts():
                return True
            else:
                return False

    def has_cervical_smear(self) -> bool:
            if '269957009' in self.snomed_concepts():
                return True
            else:
                return False

    def has_illicit_drug_use(self) -> bool:
            if '307052004' in self.snomed_concepts():
                return True
            else:
                return False

    def has_blood_test(self, blood_type: str) -> bool:
        blood_snomed_concept_ids = self.SPECIFIED_BLOOD_CODES.get(blood_type).get('snomed_concept_ids')
        blood_read_codes = self.SPECIFIED_BLOOD_CODES.get(blood_type).get('read_codes')
        read_codes = self.readcodes()
        snomed_concepts = self.snomed_concepts()

        if read_codes:
            for code in blood_read_codes:
                if code in read_codes:
                    return True
        elif snomed_concepts:
            for code in blood_snomed_concept_ids:
                if code in snomed_concepts:
                    return True
        return False

    @classmethod
    def blood_test_types(cls) -> List[str]:
        return cls.SPECIFIED_BLOOD_CODES.keys()


def load_bloods_data(filepath=''):
        if not filepath:
            filepath = os.path.join(settings.CONFIG_DIR, 'data/bloods.yml')
        with open(filepath, 'r') as stream:
            try:
                return yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)


if ValueEvent.SPECIFIED_BLOOD_CODES is None:
    ValueEvent.SPECIFIED_BLOOD_CODES = load_bloods_data()
