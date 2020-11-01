from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse

from .xml_utils import (
    chronological_redactable_elements, alphabetical_redactable_elements
)
from .medical_record import MedicalRecord
from .auto_redactable import (
    auto_redact_referrals, auto_redact_consultations, auto_redact_attachments,
    auto_redact_medications, auto_redact_profile_events, auto_redact_by_date,
    auto_redact_significant_active_problems, auto_redact_significant_past_problems,
    auto_redact_allergies, auto_redact_bloods
)
from .xml_base import XMLModelBase
from .consultation import Consultation
from .medication import Medication
from .value_event import ValueEvent
from .problem import Problem
from .referral import Referral
from .attachment import Attachment
from .xml_utils import normalize_data
from instructions.models import Instruction
from instructions import model_choices

from typing import List, Dict, TypeVar
T = TypeVar('T')


class MedicalReportDecorator(MedicalRecord):
    # todo: raw_xml type... string or bytes or something else?
    def __init__(self, raw_xml, instruction: Instruction):
        super().__init__(raw_xml)
        self.instruction = instruction

    def consultations(self) -> List[Consultation]:
        if self.instruction.type == model_choices.AMRA_TYPE:
            ret_xml = chronological_redactable_elements(
                auto_redact_consultations(
                    super().consultations(),
                    self.instruction
                )
            )
        else:
            ret_xml = auto_redact_by_date(super().consultations(),
                                          from_date=self.instruction.date_range_from,
                                          to_date=self.instruction.date_range_to,
                                          )
        return ret_xml

    def significant_active_problems(self) -> List[Problem]:
        return alphabetical_redactable_elements(
            auto_redact_significant_active_problems(
                super().significant_active_problems(),
                self.instruction
            )
        )

    def significant_past_problems(self) -> List[Problem]:
        return alphabetical_redactable_elements(
            auto_redact_significant_past_problems(
                super().significant_past_problems(),
                self.instruction
            )
        )

    def referrals(self) -> List[Referral]:
        if self.instruction.type == model_choices.AMRA_TYPE:
            ret_xml = chronological_redactable_elements(
                auto_redact_referrals(super().referrals(), self.instruction)
            )
        else:
            ret_xml = auto_redact_by_date(
                super().referrals(),
                from_date=self.instruction.date_range_from,
                to_date=self.instruction.date_range_to,
            )
        return ret_xml

    def attachments(self) -> List[Attachment]:
        ret_xml = chronological_redactable_elements(
            auto_redact_attachments(super().attachments(), self.instruction)
        )
        return ret_xml

    def acute_medications(self) -> List[Medication]:
        ret_xml = chronological_redactable_elements(
            auto_redact_medications(super().acute_medications(), self.instruction, self)
        )
        return ret_xml

    def repeat_medications(self) -> List[Medication]:
        ret_xml = chronological_redactable_elements(
            auto_redact_medications(super().repeat_medications(), self.instruction, self)
        )
        return ret_xml

    def all_allergies(self) -> List[XMLModelBase]:
        ret_xml = chronological_redactable_elements(
            auto_redact_allergies(super().all_allergies(), self.instruction)
        )
        return ret_xml

    def profile_events_for(self, event_type: str) -> List[XMLModelBase]:
        ret_xml = chronological_redactable_elements(
            auto_redact_profile_events(super().profile_event(event_type), self.instruction)
        )
        return (self.__table_elements(self.__redact_elements(ret_xml)))

    def profile_events_by_type(self) -> Dict[str, List[XMLModelBase]]:
        obj = {}
        if self.instruction.type == 'AMRA':
            for event_type in self.AMRA__PROFILE_EVENT_TYPES:
                obj[event_type] = self.profile_events_for(event_type)
        else:
            for event_type in self.SAR_PROFILE_EVENT_TYPES:
                obj[event_type] = self.profile_events_for(event_type)
        return normalize_data(obj)

    def bloods_for(self, blood_type: str) -> List[ValueEvent]:
        return (self.__table_blood_elements(self.__redact_elements(chronological_redactable_elements(
            auto_redact_bloods(super().blood_test(blood_type), self.instruction))
        )))

    def blood_test_results_by_type(self) -> Dict[str, List[ValueEvent]]:
        obj = {}
        for blood_type in ValueEvent.blood_test_types():
            result = self.bloods_for(blood_type)
            if result:
                obj[blood_type] = result
        return normalize_data(obj)

    # private
    def __table_elements(self, data: List[T]) -> List[T]:
        element_list = data
        element_list += [None] * (len(element_list))
        return list(reversed(element_list))

    def __table_blood_elements(self, data: List[T]) -> List[T]:
        element_list = list()
        if self.instruction.type == 'AMRA':
            for i in data:
                if i.parsed_date() > (datetime.now().date() - relativedelta(years=5)):
                    element_list.append(i)
        else:
            element_list = data
        return list(reversed(element_list))

    def __redact_elements(self, data: List[T]) -> List[T]:
        """
            receive elements by date from a date range from customers
        """
        element_list = list()
        if self.instruction.date_range_from:
            for i in data:
                if self.instruction.date_range_from < i.parsed_date():
                    element_list.append(i)
        if self.instruction.date_range_to:
            for i in data:
                if i.parsed_date() < self.instruction.date_range_to:
                    element_list.append(i)
        if not self.instruction.date_range_to and not self.instruction.date_range_from:
            return data
        return list(reversed(element_list))
