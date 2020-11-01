from .registration import Registration
from .consultation import Consultation
from .medication import Medication
from .allergy_event import AllergyEvent
from .allergy import Allergy
from .relation import Relation
from .value_event import ValueEvent
from .problem import Problem
from .referral import Referral
from .referral_event import ReferralEvent
from .attachment import Attachment
from .person import Person
from .location import Location
from .problem_link_list import ProblemLinkList
from .social_consultation_element import SocialConsultationElement
from .xml_base import XMLBase, XMLModelBase

from typing import List


class MedicalRecord(XMLBase):
    XPATH = './/MedicalRecord'
    SAR_PROFILE_EVENT_TYPES = [
        'height', 'weight', 'bmi', 'smoking', 'alcohol',
        'systolic_blood_pressure', 'diastolic_blood_pressure',
        'spirometry', 'peak_flow', 'cervical_smear_test',
        'illicit_drug_use'
    ]
    AMRA__PROFILE_EVENT_TYPES = [
        'height', 'weight', 'bmi', 'smoking', 'alcohol',
        'systolic_blood_pressure', 'diastolic_blood_pressure',
        'spirometry', 'peak_flow', 'cervical_smear_test',
        'illicit_drug_use'
    ]

    def consultations(self) -> List[Consultation]:
        elements = self.parsed_xml.findall(Consultation.XPATH)
        result_list = [Consultation(element) for element in elements]
        return result_list

    def registration(self) -> Registration:
        return Registration(self.parsed_xml.find(Registration.XPATH))

    def registration_status(self) -> Registration:
        return Registration(self.parsed_xml.find(Registration.REGISTRATION_STATUS_XPATH))

    def acute_medications(self) -> List[Medication]:
        return [m for m in self.__medications() if m.is_acute()]

    def repeat_medications(self) -> List[Medication]:
        return [m for m in self.__medications() if m.is_repeat()]

    # JT - This is quite dangerous - mixing a list with two different types of
    # element.
    def referrals(self) -> List[XMLModelBase]:
        referral_items = self.__referral_items()
        referral_event_items = self.__referral_event_items()
        return referral_items + referral_event_items

    def relations(self) -> List[Relation]:
        elements = self.parsed_xml.findall(Relation.XPATH)
        result_list = [Relation(element) for element in elements]
        return result_list

    def attachments(self) -> List[Attachment]:
        elements = self.parsed_xml.findall(Attachment.XPATH)
        result_list = [Attachment(element) for element in elements]
        return result_list

    def all_allergies(self) -> List[XMLModelBase]:
        allergies_list = self.__allergies()
        event_allergies = self.__event_allergies()
        return allergies_list + event_allergies

    def people(self) -> List[Person]:
        elements = self.parsed_xml.findall(Person.XPATH)
        result_list = [Person(element) for element in elements]
        return result_list

    def locations(self) -> List[Location]:
        elements = self.parsed_xml.findall(Location.XPATH)
        result_list = [Location(element) for element in elements]
        return result_list

    def problem_linked_lists(self) -> List[ProblemLinkList]:
        elements = self.parsed_xml.findall(ProblemLinkList.XPATH)
        result_list = [ProblemLinkList(element) for element in elements]
        return result_list

    def height(self) -> List[ValueEvent]:
        return [ve for ve in self.__value_events() if ve.has_height()]

    def weight(self) -> List[ValueEvent]:
        return [ve for ve in self.__value_events() if ve.has_weight()]

    def bmi(self) -> List[ValueEvent]:
        return [ve for ve in self.__value_events() if ve.has_bmi()]

    def systolic_blood_pressure(self) -> List[ValueEvent]:
        return [
            ve for ve in self.__value_events()
            if ve.has_systolic_blood_pressure()
        ]

    def diastolic_blood_pressure(self) -> List[ValueEvent]:
        return [
            ve for ve in self.__value_events()
            if ve.has_diastolic_blood_pressure()
        ]

    def blood_test(self, blood_type: str) -> List[ValueEvent]:
        return [
            ve for ve in self.__value_events()
            if ve.has_blood_test(blood_type)
        ]

    def profile_event(self, profile_event_type) -> List[XMLModelBase]:
        if profile_event_type not in self.SAR_PROFILE_EVENT_TYPES:
            return []
        event_function = getattr(self, profile_event_type)
        return event_function()

    def smoking(self) -> List[SocialConsultationElement]:
        return [
            sce for sce in self.__social_consultation_elements()
            if sce.is_smoking()
        ]

    def alcohol(self) -> List[SocialConsultationElement]:
        return [
            sce for sce in self.__social_consultation_elements()
            if sce.is_alcohol()
        ]

    def spirometry(self) -> List[ValueEvent]:
        return [
            ve for ve in self.__value_events()
            if ve.has_spirometry()
        ]

    def peak_flow(self) -> List[ValueEvent]:
        return [
            ve for ve in self.__value_events()
            if ve.has_peak_flow()
        ]

    def cervical_smear_test(self) -> List[ValueEvent]:
        return [
            ve for ve in self.__value_events()
            if ve.has_cervical_smear()
        ]

    def illicit_drug_use(self) -> List[ValueEvent]:
        return [
            ve for ve in self.__value_events()
            if ve.has_illicit_drug_use()
        ]

    def significant_active_problems(self) -> List[Problem]:
        return [sp for sp in self.__significant_problems() if sp.is_active()]

    def significant_past_problems(self) -> List[Problem]:
        return [sp for sp in self.__significant_problems() if sp.is_past()]

    def minor_problems(self) -> List[Problem]:
        return [mp for mp in self.__minor_problems()]

    # private method
    def __event_allergies(self) -> List[AllergyEvent]:
        elements = self.parsed_xml.findall(AllergyEvent.XPATH)
        result_list = [AllergyEvent(element) for element in elements]
        return result_list

    def __allergies(self) -> List[Allergy]:
        elements = self.parsed_xml.findall(Allergy.XPATH)
        result_list = [Allergy(element) for element in elements]
        return result_list

    def __medications(self) -> List[Medication]:
        elements = self.parsed_xml.findall(Medication.XPATH)
        result_list = [Medication(element) for element in elements]
        return result_list

    def __value_events(self) -> List[ValueEvent]:
        elements = self.parsed_xml.findall(ValueEvent.XPATH)
        result_list = [ValueEvent(element) for element in elements]
        return result_list

    def __social_consultation_elements(self) -> List[SocialConsultationElement]:
        elements = self.parsed_xml.xpath(SocialConsultationElement.XPATH)
        result_list = [SocialConsultationElement(element) for element in elements]
        return result_list

    def __significant_problems(self) -> List[Problem]:
        elements = self.parsed_xml.xpath(Problem.XPATH)
        problem_list = [Problem(element) for element in elements]
        return list(filter(lambda problem: problem.is_significant() is True, problem_list))

    def __minor_problems(self) -> List[Problem]:
        elements = self.parsed_xml.xpath(Problem.XPATH)
        problem_list = [Problem(element) for element in elements]
        return list(filter(lambda problem: problem.is_minor() is True, problem_list))

    def __referral_items(self) -> List[Referral]:
        elements = self.parsed_xml.findall(Referral.XPATH)
        result_list = [Referral(element) for element in elements]
        return result_list

    def __referral_event_items(self) -> List[ReferralEvent]:
        elements = self.parsed_xml.findall(ReferralEvent.XPATH)
        result_list = [ReferralEvent(element) for element in elements]
        return result_list

