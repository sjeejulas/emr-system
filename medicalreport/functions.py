from datetime import datetime
from django.conf import settings
from django.contrib import messages
from common.functions import send_mail
from django.template import loader
from django.utils.html import format_html
from django.http import HttpRequest
from django.db.models.functions import Length
from django.utils import timezone
from services.xml.medical_report_decorator import MedicalReportDecorator
from services.xml.xml_base import XMLModelBase
from snomedct.models import SnomedConcept
from services.emisapiservices import services
from services.xml.xml_utils import redaction_elements, lxml_to_string
from instructions import models
from .forms import MedicalReportFinaliseSubmitForm
from .models import AdditionalMedicationRecords, AdditionalAllergies, AmendmentsForRecord,\
        ReferencePhrases
from medicalreport.reports import MedicalReport, TEMP_DIR
from report.models import PatientReportAuth
from report.tasks import generate_medicalreport_with_attachment, send_patient_mail
from report.views import send_third_party_message
from instructions.models import Instruction
from library.models import Library, LibraryHistory

import uuid
import logging
import os
import glob
import string

UI_DATE_FORMAT = '%m/%d/%Y'
logger = logging.getLogger('timestamp')


def create_or_update_redaction_record(request, instruction: Instruction) -> bool:
    try:
        amendments_for_record = AmendmentsForRecord.objects.get(instruction=instruction)
    except AmendmentsForRecord.DoesNotExist:
        amendments_for_record = AmendmentsForRecord()
    status = request.POST.get('event_flag')

    if status != 'submit':
        get_redaction_xpaths(request, amendments_for_record)
        get_redaction_notes(request, amendments_for_record)
        get_redaction_conditions(request, amendments_for_record)
        success = get_additional_medication(request, amendments_for_record) or get_additional_allergies(request, amendments_for_record)

        delete_additional_medication_records(request)
        delete_additional_allergies_records(request)

        amendments_for_record.instruction = instruction
        questions = instruction.addition_questions.all()
        for question in questions:
            input_answer = request.POST.get('answer-question-{question_id}'.format(question_id=question.id))
            answer_obj = models.InstructionAdditionAnswer.objects.filter(question=question).first()
            if answer_obj:
                answer_obj.answer = input_answer
                answer_obj.save()
            else:
                models.InstructionAdditionAnswer.objects.create(question=question, answer=input_answer)

    if status == 'add-medication':
        if success:
            messages.success(request, 'Add Medication Successfully')
        else:
            messages.error(request, 'Missing Medication required field')
    elif status == 'add-allergies':
        if success:
            messages.success(request, 'Add Allergies Successfully')
        else:
            messages.error(request, 'Missing Allergies required field')

    if request.method == "POST":
        submit_form = MedicalReportFinaliseSubmitForm(request.user, request.POST,
                                                      initial={
                                                          'record_type': instruction.type,
                                                          'SUBMIT_OPTION_CHOICES': (
                                                              ('PREPARED_AND_SIGNED',
                                                               'Prepared and signed directly by {}'.format(
                                                                   request.user.first_name)),
                                                              ('PREPARED_AND_REVIEWED', format_html(
                                                                        'Signed off by <span id="preparer"></span>'
                                                                    ),
                                                               ),

                                                          ),
                                                      'instruction_checked': amendments_for_record.instruction_checked
                                                      },
                                                      )
        if status in ['draft', 'preview']:
            amendments_for_record.status = AmendmentsForRecord.REDACTION_STATUS_DRAFT
        elif status == 'submit':
            amendments_for_record.status = AmendmentsForRecord.REDACTION_STATUS_SUBMIT
        else:
            amendments_for_record.status = AmendmentsForRecord.REDACTION_STATUS_NEW

        if submit_form.is_valid(post_data=request.POST):
            if not status:
                amendments_for_record.instruction_checked = submit_form.cleaned_data['instruction_checked']
            amendments_for_record.submit_choice = submit_form.cleaned_data.get('prepared_and_signed')
            amendments_for_record.review_by = request.user
            if submit_form.cleaned_data.get('prepared_and_signed') == AmendmentsForRecord.PREPARED_AND_SIGNED:
                amendments_for_record.prepared_by = request.user.userprofilebase.generalpracticeuser
            else:
                amendments_for_record.prepared_by = submit_form.cleaned_data.get('prepared_by')

            if status == 'submit':
                instruction.status = models.INSTRUCTION_STATUS_FINALISE
                instruction.completed_signed_off_timestamp = timezone.now()
                messages.success(request, 'Completed Medical Report')
                delete_tmp_files(instruction)

            instruction.save()
            amendments_for_record.save()
            if status == 'preview':
                save_medical_report(instruction, amendments_for_record)
            if status and status not in ['submit', 'draft', 'preview']:
                return False
            return True
        else:
            if status not in ['add-medication', 'add-allergies']:
                messages.error(request, submit_form._errors)
            return False

    amendments_for_record.save()

    if status == 'draft':
        messages.success(request, 'Save Medical Report Successful')

    return True


def save_medical_report(instruction: Instruction, amendments_for_record: AmendmentsForRecord) -> None:
    start_time = timezone.now()
    if amendments_for_record.raw_medical_xml_encrypted:
        raw_xml = amendments_for_record.raw_medical_xml_encrypted
    else:
        raw_xml = services.GetMedicalRecord(amendments_for_record.patient_emis_number, gp_organisation=instruction.gp_practice).call()

    parse_xml = redaction_elements(raw_xml, amendments_for_record.redacted_xpaths)

    if instruction.medical_report:
        os.remove(instruction.medical_report.path)
        instruction.medical_report.delete()

    if instruction.medical_xml_report:
        os.remove(instruction.medical_xml_report.path)
        instruction.medical_xml_report.delete()

    medical_record_decorator = MedicalReportDecorator(parse_xml, instruction)
    relations = [relation.name for relation in ReferencePhrases.objects.all()]

    gp_org = instruction.gp_user.organisation
    word_library = Library.objects.filter(gp_practice=gp_org)
    library_history = LibraryHistory.objects.filter(instruction=instruction)
    relations_dict = {
        'relations': relations,
        'word_library': word_library,
        'library_history': library_history,
        'is_final_report': True
    }

    str_xml = lxml_to_string(parse_xml)
    params = {
        'medical_record': medical_record_decorator,
        'relations': relations_dict,
        'redaction': amendments_for_record,
        'instruction': instruction,
        'surgery_name': instruction.gp_practice,
    }
    instruction.final_raw_medical_xml_report = str_xml.decode('utf-8')
    instruction.medical_report_byte = MedicalReport.get_pdf_file(params, raw=True)
    instruction.save()
    end_time = timezone.now()
    total_time = end_time - start_time
    logger.info("[SAVING PDF AND XML] %s seconds with patient %s"%(total_time.seconds, instruction.patient_information.__str__()))


def delete_tmp_files(instruction: Instruction) -> None:
    for f in glob.glob(TEMP_DIR + "%s_tmp*"%instruction.pk):
        os.remove(f)


def get_redaction_xpaths(request: HttpRequest, amendments_for_record: AmendmentsForRecord) -> None:
    redaction_xpaths = request.POST.getlist('redaction_xpaths')
    amendments_for_record.redacted_xpaths = redaction_xpaths


def get_redaction_conditions(request: HttpRequest, amendments_for_record: AmendmentsForRecord) -> None:
    redaction_conditions = set(filter(None, request.POST.getlist('map_code')))
    if 'undefined'in redaction_conditions: redaction_conditions.remove('undefined')
    amendments_for_record.re_redacted_codes = list(redaction_conditions)


def get_redaction_notes(request, amendments_for_record: AmendmentsForRecord) -> None:
    acute_notes = request.POST.get('redaction_acute_prescription_notes', '')
    repeat_notes = request.POST.get('redaction_repeat_prescription_notes', '')
    consultation_notes = request.POST.get('redaction_consultation_notes', '')
    referral_notes = request.POST.get('redaction_referral_notes', '')
    significant_problem_notes = request.POST.get('redaction_significant_problem_notes', '')
    bloods_notes = request.POST.get('redaction_bloods_notes', '')
    attachment_notes = request.POST.get('redaction_attachment_notes', '')
    comment_notes = request.POST.get('redaction_comment_notes', '')

    amendments_for_record.acute_prescription_notes = acute_notes
    amendments_for_record.repeat_prescription_notes = repeat_notes
    amendments_for_record.consultation_notes = consultation_notes
    amendments_for_record.referral_notes = referral_notes
    amendments_for_record.significant_problem_notes = significant_problem_notes
    amendments_for_record.bloods_notes = bloods_notes
    amendments_for_record.attachment_notes = attachment_notes
    amendments_for_record.comment_notes = comment_notes


def get_additional_allergies(request, amendments_for_record: AmendmentsForRecord) -> bool:
    additional_allergies_allergen = request.POST.get('additional_allergies_allergen')
    additional_allergies_reaction = request.POST.get('additional_allergies_reaction')
    additional_allergies_date_discovered = request.POST.get('additional_allergies_date_discovered')

    if (additional_allergies_allergen and
            additional_allergies_reaction):
        record = AdditionalAllergies()
        record.allergen = additional_allergies_allergen
        record.reaction = additional_allergies_reaction
        if additional_allergies_date_discovered:
            record.date_discovered = datetime.strptime(additional_allergies_date_discovered, UI_DATE_FORMAT)

        record.amendments_for_record = amendments_for_record
        record.save()
        return True
    else:
        return False


def get_additional_medication(request, amendments_for_record: AmendmentsForRecord) -> bool:
    additional_medication_type = request.POST.get('additional_medication_records_type')
    additional_medication_snomedct = request.POST.get('additional_medication_related_condition')
    additional_medication_drug = request.POST.get('additional_medication_drug')
    additional_medication_dose = request.POST.get('additional_medication_dose')
    additional_medication_frequency = request.POST.get('additional_medication_frequency')
    additional_medication_prescribed_from = request.POST.get('additional_medication_prescribed_from')
    additional_medication_prescribed_to = request.POST.get('additional_medication_prescribed_to')
    additional_medication_notes = request.POST.get('additional_medication_notes')

    if (additional_medication_type and additional_medication_drug
            and additional_medication_dose and additional_medication_frequency):
        record = AdditionalMedicationRecords()
        if additional_medication_type == "acute":
            record.repeat = False
        else:
            record.repeat = True

        if additional_medication_snomedct:
            try:
                record.snomed_concept = SnomedConcept.objects.get(pk=additional_medication_snomedct)
            except SnomedConcept.DoesNotExist:
                pass
        record.dose = additional_medication_dose
        record.drug = additional_medication_drug
        record.frequency = additional_medication_frequency
        record.notes = additional_medication_notes

        if additional_medication_prescribed_from:
            record.prescribed_from = datetime.strptime(additional_medication_prescribed_from, UI_DATE_FORMAT)

        if additional_medication_prescribed_to:
            record.prescribed_to = datetime.strptime(additional_medication_prescribed_to, UI_DATE_FORMAT)

        record.amendments_for_record = amendments_for_record
        record.save()
        return True
    else:
        return False


def delete_additional_medication_records(request: HttpRequest) -> None:
    additional_medication_records_delete = request.POST.getlist('additional_medication_records_delete')
    if additional_medication_records_delete:
        AdditionalMedicationRecords.objects.filter(id__in=additional_medication_records_delete).delete()


def delete_additional_allergies_records(request: HttpRequest) -> None:
    additional_allergies_records_delete = request.POST.getlist('additional_allergies_records_delete')
    if additional_allergies_records_delete:
        AdditionalAllergies.objects.filter(id__in=additional_allergies_records_delete).delete()


def send_surgery_email(instruction: Instruction) -> None:
    send_mail(
        'Your medical report has been finalised',
        'Your instruction has been submitted',
        'MediData',
        [instruction.gp_practice.organisation_email],
        fail_silently=True,
        html_message=loader.render_to_string('medicalreport/surgery_email.html',
                                             {
                                                 'name': instruction.patient_information.patient_first_name,
                                                 'gp': instruction.gp_user.user.first_name,
                                             }
                                             ))


def create_patient_report(request: HttpRequest, instruction: Instruction) -> None:
    patient_report_auth = PatientReportAuth.objects.filter(instruction=instruction)

    if not patient_report_auth:
        unique_url = uuid.uuid4().hex
        PatientReportAuth.objects.create(patient=instruction.patient, instruction=instruction, url=unique_url)
    else:
        unique_url = patient_report_auth.first().url

    instruction_info = {
        'id': instruction.id,
        'medical_report_file_name': instruction.medical_report.name.split('/')[-1],
        'medical_xml_file_name': instruction.medical_xml_report.name.split('/')[-1]
    }
    report_link_info = {
        'scheme': request.scheme,
        'host': request.get_host(),
        'unique_url': unique_url
    }

    if settings.CELERY_ENABLED:
        generate_medicalreport_with_attachment.delay(instruction_info, report_link_info)
    else:
        generate_medicalreport_with_attachment(instruction_info, report_link_info)


def render_report_tool_box_function(header: str, xpath: str, section:str, libraries: Library, instruction: Instruction=None, library_history: LibraryHistory=None):
    split_head = header.split()
    guid = xpath[xpath.find('{') + 1: xpath.find('}')]  # get guid in xpath between bracket
    temp_header = []  # temp for concat each splitted head to final_header
    final_header = header
    library_history = library_history if library_history else LibraryHistory.objects.filter(instruction=instruction)
    replaced_indexes = set()
    skip_amount_loop = 0
    if libraries:
        libraries = libraries.order_by(Length('key').desc())
        for i, head in enumerate(split_head):
            if skip_amount_loop == 0:
                k = i
                library_matched = False
                highlight_html = '''
                    <span class="highlight-library d-inline-block">
                        <span class="{}">{}</span>
                        <span class="dropdown-options" data-guid="{}" data-word_idx="{}" data-section="{}">
                            <a href="#/" class="highlight-redact">Redact</a>
                            <a href="#/" class="highlight-replace">Replace</a>
                            <a href="#/" class="highlight-replaceall">Replace all</a>
                        </span>
                    </span>
                '''

                for library in libraries:
                    step = len(library.key.split(' '))
                    phrase = " ".join((split_head[k:k+step]))
                    if str.upper(library.key) == str.upper(phrase.replace(',', '')) and not replaced_indexes.intersection(set({k, k+step})):
                        trail = ''
                        if phrase[-1] not in string.ascii_letters + string.digits:
                            trail = phrase[-1]
                        replace_word = phrase.replace(',', '')
                        library_matched = True
                        highlight_class = 'bg-warning'

                        if not library.value:
                            highlight_html = '''
                                <span class="highlight-library d-inline-block">
                                    <span class="{}">{}</span>
                                    <span class="dropdown-options" data-guid="{}" data-word_idx="{}" data-section="{}">
                                        <a href="#/" class="highlight-redact">Redact</a>
                                    </span>
                                </span>
                            '''
                        for history in library_history:
                            action = history.action
                            if str.upper(history.old) == str.upper(phrase.replace(',', '')):
                                if action == LibraryHistory.ACTION_REPLACE \
                                        and history.guid == guid \
                                        and history.index == i \
                                        and history.section == section:
                                    replace_word = history.new
                                    highlight_class = 'text-danger'
                                    break  # already matched HISTORY exist loop
                                elif action == LibraryHistory.ACTION_HIGHLIGHT_REDACT \
                                        and history.guid == guid \
                                        and history.index == i \
                                        and history.section == section:
                                    highlight_class = 'bg-dark text-dark'
                                    break  # already matched HISTORY exist loop
                                elif action == LibraryHistory.ACTION_REPLACE_ALL:
                                    replace_word = history.new
                                    highlight_class = 'text-danger'
                                    break  # already matched HISTORY exist loop

                        replaced_indexes = replaced_indexes.union(set(list(range(k, k+step))))
                        highlight_html = highlight_html.format(highlight_class, replace_word, guid, i, section)
                        temp_header.append(highlight_html + trail)
                        skip_amount_loop = step-1
                        break  # already matched LIBRARY WORD exist loop
                k += 1

                if not library_matched:
                    temp_header.append(head)
            else:
                skip_amount_loop -= 1

        final_header = format_html(" ".join(temp_header))

    return final_header


def check_sensitive_condition(model: XMLModelBase, sensitive_conditions: dict):
    snomed_codes = set(model.snomed_concepts())
    readcodes = set(model.readcodes())
    if sensitive_conditions and \
            (sensitive_conditions['snome'].intersection(snomed_codes) or sensitive_conditions['readcodes'].intersection(readcodes)):
        return True

    return False

def send_report_notification(request, instruction, patient_report_auth, third_party_info):
    report_link_info = {
        'scheme': request.scheme,
        'host': request.get_host(),
        'unique_url': patient_report_auth.url
    }
    if instruction.patient_notification:
        send_patient_mail(
            report_link_info['scheme'],
            report_link_info['host'],
            report_link_info['unique_url'],
            instruction
        )
    if instruction.third_party_notification:
        send_third_party_message(
            third_party_info,
            report_link_info['scheme'],
            report_link_info['host'],
            patient_report_auth
        )

def redact_name_relations_third_parties(value: str, relations: list, replace_all=[]) -> str:
    for val in value.split(' '):
        original_val = val
        if original_val in relations:
            value = value.replace(val, "[UNSPECIFIED]")
        elif "'s." in original_val and original_val[:-3] in relations:
            value = value.replace(original_val[:-3], "[UNSPECIFIED]")
        elif "s'." in original_val and original_val[:-3] in relations:
            value = value.replace(original_val[:-3], "[UNSPECIFIED]")
        elif "'s" in original_val and original_val[:-2] in relations:
            value = value.replace(original_val[:-2], "[UNSPECIFIED]")
        elif "s'" in original_val and original_val[:-2] in relations:
            value = value.replace(original_val[:-2], "[UNSPECIFIED]")
        elif ":" in original_val and original_val[:-1] in relations:
            value = value.replace(original_val[:-1], "[UNSPECIFIED]")
        elif ";" in original_val and original_val[:-1] in relations:
            value = value.replace(original_val[:-1], "[UNSPECIFIED]")

        if original_val in replace_all:
            value = value.replace(val, replace_all[replace_all.index(original_val)])

    return value
