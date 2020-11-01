from services.xml.xml_base import XMLModelBase
from services.xml.medical_record import MedicalRecord

from typing import List


class ProblemLinkConditionsRedactor:
    def __init__(self, concepts: List[int] = None, readcodes: List[str] = None, medical_record: MedicalRecord = None ):
        self.concepts = concepts or []
        self.readcodes = readcodes or []
        self.medical_record = medical_record or None

    def is_redact(self, model: XMLModelBase) -> bool:
        if not self.__redactor_has_codes():
            return False
        if not self.__model_has_problem_linklist(model):
            return True
        return (
            not self.__snomed_concepts_match(self.__event_linked_model(model))
            and not self.__readcodes_match(self.__event_linked_model(model))
        )

    def __redactor_has_codes(self) -> bool:
        return bool(self.concepts or self.readcodes)

    def __snomed_concepts_match(self, model: XMLModelBase) -> bool:
        concept_code_element = model.find(".//Code[MapScheme='SNOMED']/MapCode") if model else None
        if concept_code_element:
            concept_code = concept_code_element.text
            if int(concept_code) in self.concepts:
                return True
        return False

    def __readcodes_match(self, model: XMLModelBase) -> bool:
        readcode_element = model.find(".//Code[Scheme='READ2']/Value") if model else None
        if readcode_element:
            readcode = readcode_element.text
            if readcode in self.readcodes:
                return True
        return False

    @staticmethod
    def __model_has_problem_linklist(model: XMLModelBase) -> bool:
        return bool(model.problem_linklist_guid())

    def __event_linked_model(self, model) -> XMLModelBase:
        return self.medical_record.parsed_xml.find(".//Event[GUID='{GUID}']".format(GUID=model.problem_linklist_guid()))
