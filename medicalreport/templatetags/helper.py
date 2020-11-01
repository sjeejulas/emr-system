from django import template
from django.db.models.functions import Length

from services.xml.problem import Problem
from datetime import date as Date
from typing import List, Optional
from library.models import LibraryHistory, Library
import re

register = template.Library()


def format_date(date: Optional[Date]) -> str:
    if date is None:
        return ''
    return date.strftime("%d %b %Y")


def end_date(problem: Problem) -> str:
    parsed_end_date = problem.parsed_end_date()
    if parsed_end_date is None:
        return "(ended: N/A)"
    return "(ended: {})".format(format_date(problem.parsed_end_date()))


def diagnosed_date(problem: Problem, problem_list: List[Problem]) -> str:
    dates = []
    for item in problem_list:
        dates.append(item.parsed_date())

    dates += [problem.parsed_date()]
    date = min(dates)
    if date:
        return "(diagnosed: {})".format(format_date(date))
    else:
        return ''


def additional_medication_dates_description(record):
    dates = []
    if record.prescribed_from:
        text = "from: {}".format(format_date(record.prescribed_from))
        dates += [text]
    if record.prescribed_to:
        text = "to: {}".format(format_date(record.prescribed_to))
        dates += [text]

    if any(dates):
        return "({})".format(' '.join(dates))
    else:
        return ''


def linked_problems(problem, problem_list):
    filterd_list = filter(lambda x: problem.guid() in x.target_guids(), problem_list)
    return list(filterd_list)


def problem_xpaths(problem, problem_link_list):
    problem_link_xpaths = []
    for link in linked_problems(problem, problem_link_list):
        problem_link_xpaths += link.xpaths()

    xpaths = problem.xpaths() + problem_link_xpaths
    return [xpaths[0]]


def render_toolbox_function_for_final_report(library_history: LibraryHistory = None, xpath: str = '', value: str = '', libraries: Library=None, section: str = ''):
    guid = xpath[xpath.find('{') + 1: xpath.find('}')]
    section_library_histories = library_history.filter(section=section)

    if section_library_histories:
        for section_library_history in section_library_histories:
            if section_library_history.action == LibraryHistory.ACTION_HIGHLIGHT_REDACT and \
                    section_library_history.guid == guid:
                value = value.replace(section_library_history.old, '')
            elif section_library_history.action == LibraryHistory.ACTION_REPLACE and \
                    section_library_history.guid == guid:
                value = value.replace(section_library_history.old, section_library_history.new)

    for replace_all_history in library_history.filter(action=LibraryHistory.ACTION_REPLACE_ALL):
        value = re.sub(replace_all_history.old, replace_all_history.new, value, flags=re.IGNORECASE)

    return value
