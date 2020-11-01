from services.xml.xml_base import XMLModelBase

from typing import List


class ConditionsRedactor:
    def __init__(self, concepts: List[int] = None, readcodes: List[str] = None):
        self.concepts = concepts or []
        self.readcodes = readcodes or []

    def is_redact(self, model: XMLModelBase) -> bool:
        if not self.__redactor_has_codes():
            return False
        if not self.__model_has_codes(model):
            return True
        return (
            not self.__snomed_concepts_match(model)
            and not self.__readcodes_match(model)
        )

    def __redactor_has_codes(self) -> bool:
        return bool(self.concepts or self.readcodes)

    @staticmethod
    def __model_has_codes(model: XMLModelBase) -> bool:
        return bool(model.snomed_concepts() or model.readcodes())

    def __snomed_concepts_match(self, model: XMLModelBase) -> bool:
        snomed_concepts = model.snomed_concepts()
        for concept in snomed_concepts:
            if int(concept) in self.concepts:
                return True
        return False

    def __readcodes_match(self, model: XMLModelBase) -> bool:
        readcodes = model.readcodes()
        for code in readcodes:
            if code in self.readcodes:
                return True
        return False
