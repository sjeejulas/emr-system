from datetime import date
from ..autoredactors.date_redactor import DateRedactor
from ..autoredactors.conditions_redactor import ConditionsRedactor
from ..autoredactors.problem_link_conditions_redactor import ProblemLinkConditionsRedactor
from services.xml.xml_base import XMLModelBase
from instructions.models import Instruction
from instructions.model_choices import AMRA_TYPE

from dateutil.relativedelta import relativedelta
from typing import Iterable, List


def years_ago(years: int, current_date: date) -> date:
    return current_date - relativedelta(years=years)


def auto_redact_by_conditions(
        models: Iterable[XMLModelBase],
        instruction: Instruction
) -> List[XMLModelBase]:
    snomed_concepts_ids, readcodes = instruction.snomed_concepts_ids_and_readcodes()
    redactor = ConditionsRedactor(
        concepts=list(snomed_concepts_ids),
        readcodes=list(readcodes)
    )
    return [m for m in models if not redactor.is_redact(m)]


def auto_redact_by_link_conditions(
        models: Iterable[XMLModelBase],
        instruction: Instruction,
        medical_record: XMLModelBase
) -> List[XMLModelBase]:
    snomed_concepts_ids, readcodes = instruction.snomed_concepts_ids_and_readcodes()
    redactor = ProblemLinkConditionsRedactor(
        concepts=list(snomed_concepts_ids),
        readcodes=list(readcodes),
        medical_record=medical_record
    )

    return [m for m in models if not redactor.is_redact(m)]


def auto_redact_by_date(
        models: Iterable[XMLModelBase],
        start_date=None,
        from_date=None,
        to_date=None,
) -> List[XMLModelBase]:
    if from_date:
        start_date = from_date
    redactor = DateRedactor(start_date=start_date, from_date=from_date, to_date=to_date)
    return [m for m in models if not redactor.is_redact(m)]


def auto_redact_consultations(consultations, instruction, current_date=date.today()):
    start_date = None
    if instruction.type == AMRA_TYPE:
        start_date = years_ago(5, current_date)
    return auto_redact_by_date(
        auto_redact_by_conditions(consultations, instruction),
        start_date=start_date, from_date=instruction.date_range_from, to_date=instruction.date_range_to
    )


def auto_redact_medications (medications, instruction, medical_record, current_date=date.today()):
    start_date = None
    if instruction.type == AMRA_TYPE:
        start_date = years_ago(5, current_date)
        return auto_redact_by_date(
            auto_redact_by_link_conditions(medications, instruction, medical_record),
            start_date=start_date, from_date=instruction.date_range_from, to_date=instruction.date_range_to
        )
    else:
        return auto_redact_by_date(
            medications,
            start_date=start_date, from_date=instruction.date_range_from, to_date=instruction.date_range_to
        )


def auto_redact_significant_active_problems(significant_active_problems, instruction, current_date=date.today()):
    start_date = None
    if instruction.type == AMRA_TYPE:
        start_date = years_ago(5, current_date)
    return auto_redact_by_date(significant_active_problems, start_date=start_date, from_date=instruction.date_range_from, to_date=instruction.date_range_to)


def auto_redact_significant_past_problems(significant_past_problems, instruction, current_date=date.today()):
    start_date = None
    if instruction.type == AMRA_TYPE:
        start_date = years_ago(5, current_date)
    return auto_redact_by_date(significant_past_problems, start_date=start_date, from_date=instruction.date_range_from, to_date=instruction.date_range_to)


def auto_redact_referrals(referrals, instruction, current_date=date.today()):
    start_date = None
    if instruction.type == AMRA_TYPE:
        start_date = years_ago(5, current_date)
    return auto_redact_by_date(
        auto_redact_by_conditions(referrals, instruction),
        start_date=start_date, from_date=instruction.date_range_from, to_date=instruction.date_range_to
    )


def auto_redact_attachments(attachments, instruction, current_date=date.today()):
    start_date = None
    if instruction.type == AMRA_TYPE:
        start_date = years_ago(2, current_date)
    return auto_redact_by_date(attachments, start_date=start_date, from_date=instruction.date_range_from, to_date=instruction.date_range_to)


def auto_redact_profile_events(events, instruction, current_date=date.today()):
    start_date = None
    if instruction.type == AMRA_TYPE:
        start_date = years_ago(5, current_date)
    return auto_redact_by_date(events, start_date=start_date, from_date=instruction.date_range_from, to_date=instruction.date_range_to)


def auto_redact_allergies(events, instruction, current_date=date.today()):
    start_date = None
    return auto_redact_by_date(events, start_date=start_date, from_date=instruction.date_range_from, to_date=instruction.date_range_to)


def auto_redact_bloods(events, instruction, current_date=date.today()):
    start_date = None
    return auto_redact_by_date(events, start_date=start_date, from_date=instruction.date_range_from, to_date=instruction.date_range_to)
