from django import template

from library.models import Library
from services.xml.xml_base import XMLModelBase
from medicalreport.models import AmendmentsForRecord, RedactedAttachment
from medicalreport.functions import render_report_tool_box_function, check_sensitive_condition
from .helper import problem_xpaths

register = template.Library()


@register.inclusion_tag('medicalreport/inclusiontags/patient_info.html', takes_context=True)
def patient_info(context):
    return {
        'medical_record': context['medical_record'],
        'instruction': context['instruction']
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_referrals.html', takes_context=True)
def form_referrals(context):
    return {
        'referrals': context['medical_record'].referrals,
        'locations': context['medical_record'].locations,
        'instruction': context['instruction'],
        'minor_problems_list': context['medical_record'].minor_problems,
        'redaction': context['redaction'],
        'word_library': context['word_library'],
        'sensitive_conditions': context['sensitive_conditions'],
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_attachments.html', takes_context=True)
def form_attachments(context):
    return {
        'attachments': context['medical_record'].attachments,
        'instruction': context['instruction'],
        'redacted_attachments': context['redacted_attachments'],
        'redaction': context['redaction'],
        'section': 'attachments',
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_consultations.html', takes_context=True)
def form_consultations(context):
    return {
        'consultations': context['medical_record'].consultations,
        'relations': context['relations'],
        'people': context['medical_record'].people,
        'redaction': context['redaction'],
        'word_library': context['word_library'],
        'sensitive_conditions': context['sensitive_conditions'],
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_profile.html', takes_context=True)
def form_profile(context):
    return {
        'profile_events': context['medical_record'].profile_events_by_type,
        'profile_sex': context['medical_record'].registration().sex()
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_bloods.html', takes_context=True)
def form_bloods(context):
    return {
        'results': context['medical_record'].blood_test_results_by_type,
        'redaction': context['redaction'],
        'instruction_type': context['instruction'].type
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_significant_problems.html', takes_context=True)
def form_significant_problems(context):
    return {
        'significant_active_problems': context['medical_record'].significant_active_problems,
        'significant_past_problems': context['medical_record'].significant_past_problems,
        'problem_linked_lists': context['medical_record'].problem_linked_lists,
        'redaction': context['redaction'],
        'word_library': context['word_library'],
        'sensitive_conditions': context['sensitive_conditions'],
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_medications.html', takes_context=True)
def form_medications(context):
    return {
        'acute_medications': context['medical_record'].acute_medications,
        'repeat_medications': context['medical_record'].repeat_medications,
        'additional_acute_medications': context['redaction'].additional_acute_medications,
        'additional_repeat_medications': context['redaction'].additional_repeat_medications,
        'redaction': context['redaction'],
        'instruction': context['instruction'],
        'word_library': context['word_library'],
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_additional_medications.html')
def form_additional_medications(additional_medication_records):
    return {
        'additional_medication_records': additional_medication_records
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_new_additional_medications.html')
def form_new_additional_medications(instruction):
    return {
        'instruction': instruction
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_allergies.html', takes_context=True)
def form_allergies(context):
    return {
        'all_allergies': context['medical_record'].all_allergies,
        'additional_allergies': context['redaction'].additional_allergies,
        'redaction': context['redaction'],
        'instruction': context['instruction'],
        'word_library': context['word_library'],
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_additional_allergies.html')
def form_additional_allergies(additional_allergies_records, word_library):
    return {
        'additional_allergies_records': additional_allergies_records,
        'word_library': word_library
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_new_additional_allergies.html')
def form_new_additional_allergies():
    return {}


@register.inclusion_tag('medicalreport/inclusiontags/redaction_checkbox_with_body.html')
def redaction_checkbox_with_body(
    model: XMLModelBase, redaction: AmendmentsForRecord, header: str,
    libraries: Library=None, sensitive_conditions: dict={}, section: str=''):

    title = header
    checked = ""
    xpaths = model.xpaths()

    # checking sensitive conditions
    is_sensitive = check_sensitive_condition(model=model, sensitive_conditions=sensitive_conditions)

    # checking redacted
    if (redaction.redacted(xpaths) is True) or is_sensitive:
        checked = "checked"

    redacted_count = 0
    if section == 'attachments':
        dds_identifier = model.dds_identifier()
        redacted_count = RedactedAttachment.objects.filter(
            instruction=redaction.instruction,
            dds_identifier=dds_identifier
        ).values_list('redacted_count', flat=True)

        # Todo REMOVE FILE SYSTEM SUPPORT
        if redacted_count:
            redacted_count = redacted_count[0]
        else:
            redacted_count = -1  # attachment still not redacted

    # rendering report toolbox function
    final_header = render_report_tool_box_function(
        header=header, xpath=xpaths[0], section=section, libraries=libraries, instruction=redaction.instruction
    )

    return {
        'checked': checked,
        'xpaths': xpaths,
        'header': header,
        'title': title,
        'header_detail': final_header,
        'is_sensitive': is_sensitive,
        'section': section,
        'redacted_count': redacted_count,
    }


@register.inclusion_tag('medicalreport/inclusiontags/redaction_checkbox_with_list.html')
def redaction_checkbox_with_list(model, redaction, header='', dict_data='', map_code='', label=None, relations='', sensitive_conditions={}):
    checked = ""
    if redaction.re_redacted_codes:
        sensitive_conditions['snome'] - set(redaction.re_redacted_codes)

    is_sensitive_consultation = False
    if sensitive_conditions['snome'].intersection(set(map_code)) or sensitive_conditions['readcodes'].intersection(set(model.readcodes())):
        checked = "checked"
        is_sensitive_consultation = True

    xpaths = model.xpaths()
    if redaction.redacted(xpaths) is True:
        checked = "checked"

    relations['xpath'] = xpaths
    return {
        'redaction_checks': redaction.redacted_xpaths,
        're_redaced_codes': redaction.re_redacted_codes,
        'checked': checked,
        'relations': relations,
        'xpaths': xpaths,
        'header': header,
        'dict_data': dict_data,
        'label': label,
        'sensitive_conditions': sensitive_conditions,
        'is_sensitive_consultation': is_sensitive_consultation
    }


@register.inclusion_tag('medicalreport/inclusiontags/redaction_checkbox_with_body.html')
def problem_redaction_checkboxes(
        model: XMLModelBase, redaction: AmendmentsForRecord, problem_linked_lists,
        header: str, libraries: Library, map_code: list, sensitive_conditions: dict, section: str):

    title = header
    checked = ""
    xpaths = problem_xpaths(model, problem_linked_lists)

    if redaction.re_redacted_codes:
        sensitive_conditions['snome'] - set(redaction.re_redacted_codes)

    is_sensitive = check_sensitive_condition(model=model, sensitive_conditions=sensitive_conditions)

    if (redaction.redacted(xpaths) is True) or is_sensitive:
        checked = "checked"

    final_header = render_report_tool_box_function(
        header=header, xpath=xpaths[0], section=section, libraries=libraries, instruction=redaction.instruction
    )

    return {
            'checked': checked,
            'xpaths': xpaths,
            'header': header,
            'title': title,
            'header_detail': final_header,
            'is_sensitive': is_sensitive
        }


@register.inclusion_tag('medicalreport/inclusiontags/form_comments.html', takes_context=True)
def form_comments(context):
    return {
        'comment_notes': context['redaction'].comment_notes
    }


@register.inclusion_tag('medicalreport/inclusiontags/form_addition_answers.html', takes_context=True)
def form_addition_answers(context):
    return {
        'questions': context['questions']
    }
