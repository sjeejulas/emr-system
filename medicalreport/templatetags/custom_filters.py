from django import template
from django.utils.html import format_html
from .helper import diagnosed_date, linked_problems, end_date, format_date, additional_medication_dates_description, render_toolbox_function_for_final_report, problem_xpaths

import re
register = template.Library()


@register.filter
def get_attachment(redacted_attachments, dds_identifier):
    return redacted_attachments.filter(dds_identifier=dds_identifier).exists()


@register.filter
def instruction_patient_address(patient_information):
    address_lines = [
        patient_information.patient_postcode,
        patient_information.patient_address_number,
    ]
    address_lines = list(filter(None, address_lines))
    return ", ".join(address_lines)


@register.filter
def patient_address(patient):
    address = patient.address_lines()
    return ", ".join(address)

@register.filter
def patient_description(patient):
    description = [patient.full_name(), format_date(patient.parsed_date_of_birth())] + patient.address_lines()
    description = list(filter(None, description))
    description = ", ".join(description)
    return description


@register.filter
def format_date_filter(date):
    return format_date(date)


@register.filter
def additional_medication_header(record):
    fsn_description = ''
    if record.snomed_concept is not None:
        fsn_description = record.snomed_concept.fsn_description
    medical_addition = record.drug
    if fsn_description:
        medical_addition += "prescribed for {}".format(fsn_description)
    return medical_addition


@register.filter
def additional_medication_body(record):
    medical_addition = "{} {} {}.".format(
        record.dose, record.frequency, additional_medication_dates_description(record))
    if record.notes:
        medical_addition += " Additional contextual information:{}".format(record.notes)
    return medical_addition

#
@register.filter
def additional_allergy_description(record, word_library):
    prefix = ''
    if record.date_discovered:
        prefix = "{} - ".format(format_date(record.date_discovered))

    text_allergen = record.allergen
    text_reaction = record.reaction
    for word in word_library:
        if str.upper(word.key) == str.upper(text_allergen):
            text_allergen = '''
                <span class="highlight-library d-inline-block">
                    <span class="bg-warning">%s</span>
                    <span class="dropdown-options">
                        <a href="#" class="highlight-redact">Redact</a>
                        <a href="#" class="highlight-replace">Replace</a>
                        <a href="#" class="highlight-replaceall">Replace all</a>
                    </span>
                </span>
            ''' % (text_allergen)
        if str.upper(word.key) == str.upper(text_reaction):
            text_reaction = '''
                <span class="highlight-library d-inline-block">
                    <span class="bg-warning">%s</span>
                    <span class="dropdown-options">
                        <a href="#" class="highlight-redact">Redact</a>
                        <a href="#" class="highlight-replace">Replace</a>
                        <a href="#" class="highlight-replaceall">Replace all</a>
                    </span>
                </span>
            ''' % (text_reaction)
    return format_html("{}{}, {}".format(prefix, text_allergen, text_reaction))


@register.filter
def active_problem_header(problem, problem_params):
    if type(problem_params) == dict:
        problem_list = problem_params['problem_list']
        library_history = problem_params['relations']['library_history']
        libraries = problem_params['relations']['word_library']
        xpath = problem.xpaths()[0]
        description = render_toolbox_function_for_final_report(library_history, xpath, problem.description(), libraries=libraries, section='significant_active')
        return "{} {}".format(description, diagnosed_date(problem, linked_problems(problem, problem_list())))
    else:
        problem_list = problem_params
        return "{} {}".format(problem.description(), diagnosed_date(problem, linked_problems(problem, problem_list)))


@register.filter
def past_problem_header(problem, problem_params):
    if type(problem_params) == dict:
        library_history = problem_params['relations']['library_history']
        libraries = problem_params['relations']['word_library']
        xpath = problem.xpaths()[0]
        description = render_toolbox_function_for_final_report(library_history, xpath, problem.description(), libraries=libraries, section='significant_past')
        return "{} {}".format(description, end_date(problem))
    else:
        return "{} {}".format(problem.description(), end_date(problem))


@register.filter
def general_header(model, toolbox_params=''):
    if type(toolbox_params) == dict:
        library_history = toolbox_params['relations']['library_history']
        libraries = toolbox_params['relations']['word_library']
        xpath = model.xpaths()[0]
        description = render_toolbox_function_for_final_report(library_history, xpath, model.description(), libraries=libraries, section=toolbox_params['section'])
        text = "{} - {}".format(format_date(model.parsed_date()), description)
        return format_html(text)
    else:
        return "{} - {}".format(format_date(model.parsed_date()), model.description())


@register.filter
def referral_body(referral, locations):
    provider = None
    for location in locations:
        if location.ref_id() == referral.provider_refid():
            provider = location
            break
    try:
        return ', '.join(provider.address_lines())
    except:
        return ''


@register.filter
def is_linked_with_minor_problem(referral, minor_problems_list):
    guid_minor_problems = [p.get_element_text('GUID') for p in minor_problems_list]
    return referral.get_element_text('ProblemLinkList/Link/Target/GUID') in guid_minor_problems


@register.filter
def consultation_header(consultation, people):
    author = None
    for p in people:
        if p.ref_id() == consultation.original_author_refid():
            author = p
    if author is not None:
        return "{} - {}".format(format_date(consultation.parsed_date()), author.full_name())
    else:
        return format_date(consultation.parsed_date())


@register.filter
def consultaion_sick_note(consultation):
    if consultation.is_sick_note():
        return 'sick note'
    else:
        return None


@register.filter
def profile_event_value_header(key):
    header = {
        "height": "Height",
        "weight": "Weight",
        "bmi": "BMI",
        "smoking": "Smoking",
        "alcohol": "Alcohol",
        "systolic_blood_pressure": "Systolic Blood Pressure",
        "diastolic_blood_pressure": "Diastolic Blood Pressure",
        "spirometry": "Spirometry (FVC, FEV1)",
        "peak_flow": "Peak flow",
        "cervical_smear_test": "Cervical smear test",
        "illicit_drug_use": "Illicit drug use"
    }
    return header[key]


@register.filter
def event_value_body(event):
    if event:
        return "{}<br>{}".format(format_date(event.parsed_date()), event.description())
    else:
        return "N/A"


@register.filter
def bloods_type_value_header(key):
    header = {
        "white_blood_count": "WBC",
        "hemoglobin": "Hb",
        "platelets": "Platelets",
        "mean_cell_volume": "MCV",
        "mean_corpuscular_hemoglobin": "MCH",
        "neutrophils": "Neutrophils",
        "lymphocytes": "Lymphocytes",
        "sodium": "Sodium",
        "potassium": "Potassium",
        "urea": "Urea",
        "creatinine": "Creatinine",
        "c_reactive_protein": "CRP",
        "bilirubin": "Bilirubin",
        "alkaline_phosphatase": "ALP",
        "alanine_aminotransferase": "ALT",
        "albumin": "Albumin",
        "gamma_gt": "Gamma-GT",
        "triglycerides": "Triglycerides",
        "total_cholesterol": "Total Cholesterol",
        "high_density_lipoprotein": "HDL",
        "low_density_lipoprotein": "LDL",
        "random_glucose": "Random Glucose",
        "fasting_glucose": "Fasting Glucose",
        "hba1c": "HbA1c",
    }
    return header[key]


@register.filter
def consultation_element_list(consultation):
    data = list()
    regex = re.compile(r"\.\s*\Z", re.IGNORECASE)
    for element in consultation.consultation_elements():
        header = element.header()
        obj = {}
        if header in obj:
            obj[header] = regex.sub('', obj[header]) + '. {}'.format(element.content().description())
        else:
            obj[header] = element.content().description()
        obj['xpath'] = element.xpaths()
        obj['map_code'] = element.map_code()
        data.append(obj)
    return data


@register.filter
def replace_ref_phrases(relations, value):
    libraries = relations.get('word_library')
    library_history = relations.get('library_history')
    is_final_report = relations.get('is_final_report', False)
    xpaths = relations.get('xpath')

    from medicalreport.functions import redact_name_relations_third_parties
    if relations.get('relations'):
        value = redact_name_relations_third_parties(value, relations['relations'])

    final_header = value

    from medicalreport.functions import render_report_tool_box_function
    if libraries:
        if is_final_report:
            final_header = render_toolbox_function_for_final_report(library_history, xpaths[0], value, libraries=libraries, section='consultations')
        else:
            final_header = render_report_tool_box_function(
                header=value, xpath=xpaths[0], section='consultations', libraries=libraries, library_history=library_history
            )
            return final_header

    return final_header


@register.filter
def map_code(consultation):
    return consultation.map_code()


@register.filter
def mod_column(count):
    max_column = 4
    if not (count-1) % max_column:
        return True
    return False


@register.filter
def hash(h, key):
    return h[key]


@register.filter
def modify_section(modified_dict, new_section):
    modified_dict['section'] = new_section

    return modified_dict


@register.filter
def add_xpath(relations:dict, dict_data:dict):
    for key, value in dict_data.items():
        if key == 'xpath':
            relations['xpath'] = value

    return relations
