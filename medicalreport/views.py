import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse, HttpRequest
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from services.emisapiservices import services
from services.xml.medical_report_decorator import MedicalReportDecorator
from services.xml.medical_record import MedicalRecord
from .models import AmendmentsForRecord, ReferencePhrases, NhsSensitiveConditions
from services.xml.patient_list import PatientList
from services.xml.registration import Registration
from medicalreport.forms import MedicalReportFinaliseSubmitForm
from medicalreport.reports import AttachmentReport
from medicalreport.models import RedactedAttachment
from instructions.models import Instruction, InstructionPatient
from instructions.model_choices import INSTRUCTION_REJECT_TYPE, AMRA_TYPE, INSTRUCTION_STATUS_REJECT
from instructions.forms import ConsentThirdParty
from .functions import create_or_update_redaction_record, create_patient_report, send_report_notification
from accounts.models import  Patient, GENERAL_PRACTICE_USER
from organisations.models import OrganisationGeneralPractice
from .forms import AllocateInstructionForm
from permissions.functions import check_permission, check_user_type
from payment.functions import calculate_instruction_fee
from typing import List
from common.functions import multi_getattr
from library.forms import LibraryForm
from library.models import Library, LibraryHistory
from wsgiref.util import FileWrapper
from django.core import serializers
from report.models import PatientReportAuth, ThirdPartyAuthorisation
from accounts.forms import InstructionPatientForm
#from silk.profiling.profiler import silk_profile

import uuid

logger = logging.getLogger('timestamp')
event_logger = logging.getLogger('medidata.event')


@login_required(login_url='/accounts/login')
def view_attachment(request: HttpRequest, instruction_id: str, path_file: str) -> HttpResponse:
    instruction = get_object_or_404(Instruction, pk=instruction_id)
    redacted_attachment = RedactedAttachment.objects.filter(instruction_id=instruction.id, dds_identifier=path_file).first()
    if request.is_ajax():
        if redacted_attachment:
            return JsonResponse({'have_report': True, 'redacted_count': redacted_attachment.redacted_count}, status=200)
        else:
            return JsonResponse({'have_report': False}, status=200)
    if redacted_attachment:
        if redacted_attachment.name.split('.')[-1] in ["pdf", "rtf", "doc", "docx", "jpg", "jpeg", "png", "tiff", "tif"]:
            response = HttpResponse(
                bytes(redacted_attachment.raw_attachment_file_content),
                content_type="application/pdf",
            )
            return response
        else:
            return AttachmentReport.render_download_file(redacted_attachment.dds_identifier, instruction.id)
    else:
        raw_xml_or_status_code = services.GetAttachment(instruction.patient_information.patient_emis_number, path_file, gp_organisation=instruction.gp_practice).call()
        if isinstance(raw_xml_or_status_code, int):
            return redirect('services:handle_error', code=raw_xml_or_status_code)
        attachment_report = AttachmentReport(instruction, raw_xml_or_status_code, path_file)
        return attachment_report.render()


@login_required(login_url='/accounts/login')
def download_attachment(request: HttpRequest, instruction_id: str, path_file: str) -> HttpResponse:
    instruction = get_object_or_404(Instruction, pk=instruction_id)
    redacted_attachment = RedactedAttachment.objects.filter(instruction_id=instruction.id, dds_identifier=path_file).first()
    if redacted_attachment:
        if redacted_attachment.name.split('.')[-1] in ["pdf", "rtf", "doc", "docx", "jpg", "jpeg", "png", "tiff", "tif"]:
            response = HttpResponse(
                bytes(redacted_attachment.raw_attachment_file_content),
                content_type="application/octet-stream"
            )
            response['Content-Disposition'] = 'attachment; filename=' + redacted_attachment.name
            return response

    raw_xml_or_status_code = services.GetAttachment(instruction.patient_information.patient_emis_number, path_file, gp_organisation=instruction.gp_practice).call()
    if isinstance(raw_xml_or_status_code, int):
        return redirect('services:handle_error', code=raw_xml_or_status_code)
    attachment_report = AttachmentReport(instruction, raw_xml_or_status_code, path_file)
    return attachment_report.download()


@login_required(login_url='/accounts/login')
def download_medicalreport(request: HttpRequest, instruction_id: str) -> HttpResponse:
    instruction = get_object_or_404(Instruction, pk=instruction_id)
    file_name = '_'.join([
        'medicalreport',
        instruction.patient_information.patient_first_name,
        instruction.patient_information.patient_last_name,
        str(timezone.now()).split(' ')[0]
    ])

    if not instruction.medical_report:
        response = HttpResponse(bytes(instruction.medical_report_byte), content_type="application/octet-stream")
    else:
        path_file = instruction.medical_report.path
        response = HttpResponse(FileWrapper(open(path_file, 'rb')), content_type="application/octet-stream")

    response['Content-Disposition'] = 'attachment; filename=' + file_name + ".pdf"

    return response


def get_matched_patient(patient: Patient, gp_organisation: OrganisationGeneralPractice) -> List[Registration]:
    raw_xml_or_status_code = services.GetPatientList(patient, gp_organisation=gp_organisation).call()
    if isinstance(raw_xml_or_status_code, int):
        return redirect('services:handle_error', code=raw_xml_or_status_code)
    patients = PatientList(raw_xml_or_status_code).patients()
    return patients


def get_patient_registration(patient_number: str, gp_organisation: OrganisationGeneralPractice) -> Registration:
    raw_xml_or_status_code = services.GetMedicalRecord(patient_number, gp_organisation=gp_organisation).call()
    if isinstance(raw_xml_or_status_code, int):
        return redirect('services:handle_error', code=raw_xml_or_status_code)
    patient_registration = MedicalRecord(raw_xml_or_status_code).registration()
    return patient_registration


@login_required(login_url='/accounts/login')
@check_user_type(GENERAL_PRACTICE_USER)
def reject_request(request: HttpRequest, instruction_id: str) -> HttpResponse:
    instruction = Instruction.objects.get(id=instruction_id)
    instruction.reject(request, request.POST)
    event_logger.info(
        '{user}:{user_id} REJECT instruction ID {instruction_id}'.format(
            user=request.user, user_id=request.user.id,
            instruction_id=instruction_id
        )
    )
    return HttpResponseRedirect("%s?%s"%(reverse('instructions:view_pipeline'),"status=%s&type=allType"%INSTRUCTION_STATUS_REJECT))


@login_required(login_url='/accounts/login')
@check_user_type(GENERAL_PRACTICE_USER)
def select_patient(request: HttpRequest, instruction_id: str, patient_emis_number: int) -> HttpResponseRedirect:
    instruction = get_object_or_404(Instruction, pk=instruction_id)
    patient_instruction = instruction.patient_information
    patient_instruction.patient_emis_number = patient_emis_number
    patient_instruction.save()
    instruction.gp_user = request.user.userprofilebase.generalpracticeuser
    instruction.save()
    messages.success(request, 'Allocated to self successful')

    if not AmendmentsForRecord.objects.filter(instruction=instruction).exists():
        raw_xml = services.GetMedicalRecord(patient_emis_number, gp_organisation=instruction.gp_practice).call()
        aes_key = uuid.uuid4().hex
        # create AmendmentsForRecord with aes_key first then save raw_xml and encrypted with self aes_key
        amendments = AmendmentsForRecord.objects.create(instruction=instruction, raw_medical_xml_aes_key=aes_key)
        amendments.raw_medical_xml_encrypted = raw_xml
        amendments.save()

    instruction.in_progress(context={'gp_user': request.user.userprofilebase.generalpracticeuser})
    instruction.saved = False
    instruction.save()
    event_logger.info(
        '{user}:{user_id} SELECTED EMIS patient ID {patient_emis_number} on instruction ID {instruction_id}'.format(
            user=request.user, user_id=request.user.id,
            patient_emis_number=patient_emis_number,
            instruction_id=instruction_id
        )
    )
    return redirect('medicalreport:edit_report', instruction_id=instruction_id)


@login_required(login_url='/accounts/login')
@check_permission
@check_user_type(GENERAL_PRACTICE_USER)
def set_patient_emis_number(request: HttpRequest, instruction_id: str) -> HttpResponse:
    instruction = Instruction.objects.get(id=instruction_id)
    patient_list = get_matched_patient(instruction.patient_information, gp_organisation=instruction.gp_practice)
    if isinstance(patient_list, HttpResponseRedirect):
        return patient_list
    event_logger.info(
        '{user}:{user_id} ACCESS select EMIS patient List view'.format(
            user=request.user, user_id=request.user.id,
        )
    )

    return render(request, 'medicalreport/patient_emis_number.html', {
        'patient_list': patient_list,
        'reject_types': INSTRUCTION_REJECT_TYPE,
        'instruction': instruction,
        'amra_type': AMRA_TYPE,
        'patient_full_name': instruction.patient_information.get_full_name()
    })


@login_required(login_url='/accounts/login')
@check_permission
#@silk_profile(name='Edit Report')
@check_user_type(GENERAL_PRACTICE_USER)
def edit_report(request: HttpRequest, instruction_id: str) -> HttpResponse:
    instruction = get_object_or_404(Instruction, id=instruction_id)
    try:
        redaction = AmendmentsForRecord.objects.get(instruction=instruction_id)
    except AmendmentsForRecord.DoesNotExist:
        return redirect('medicalreport:set_patient_emis_number', instruction_id=instruction_id)

    # Todo REMOVE FILE SYSTEM SUPPORT
    if redaction.raw_medical_xml_encrypted:
        raw_xml_or_status_code = redaction.raw_medical_xml_encrypted
    else:
        raw_xml_or_status_code = services.GetMedicalRecord(redaction.patient_emis_number, gp_organisation=instruction.gp_practice).call()

    medical_record_decorator = MedicalReportDecorator(raw_xml_or_status_code, instruction)
    start_time = timezone.now()
    questions = instruction.addition_questions.all()
    initial_prepared_by = request.user.userprofilebase.generalpracticeuser.pk
    if redaction.prepared_by:
        initial_prepared_by = redaction.prepared_by.pk
    finalise_submit_form = MedicalReportFinaliseSubmitForm(
        initial={
            'record_type': redaction.instruction.type,
            'SUBMIT_OPTION_CHOICES': (
                    ('PREPARED_AND_REVIEWED', format_html(
                        'Signed off by <span id="preparer"></span>'.format(request.user.first_name)),
                     ),
                ),
            'prepared_by': initial_prepared_by,
            'prepared_and_signed': redaction.submit_choice or AmendmentsForRecord.PREPARED_AND_REVIEWED,
            'instruction_checked': redaction.instruction_checked
        },
        user=request.user)

    relations = [relation.name for relation in ReferencePhrases.objects.all()]
    sensitive_conditions = dict()
    sensitive_conditions['snome'] = set(NhsSensitiveConditions.objects.all().values_list('snome_code', flat=True))
    sensitive_conditions['readcodes'] = NhsSensitiveConditions.get_sensitives_readcode()

    inst_gp_user = instruction.gp_user.user
    cur_user = request.user
    event_logger.info(
        '{user}:{user_id} ACCESS edit medical report view'.format(
            user=request.user, user_id=request.user.id,
        )
    )

    gp_practice_code = multi_getattr(request, 'user.userprofilebase.generalpracticeuser.organisation.pk', default=None)
    library_form = LibraryForm(gp_org_id=gp_practice_code)

    word_library = Library.objects.filter(gp_practice=gp_practice_code)
    library_history = LibraryHistory.objects.filter(instruction=instruction)

    relations = {
        'relations': relations,
        'word_library': word_library,
        'library_history': library_history,
    }

    redacted_attachments = RedactedAttachment.objects.filter(instruction_id=instruction.id)
    response = render(request, 'medicalreport/medicalreport_edit.html', {
        'user': request.user,
        'medical_record': medical_record_decorator,
        'redaction': redaction,
        'instruction': instruction,
        'redacted_attachments': redacted_attachments,
        'finalise_submit_form': finalise_submit_form,
        'questions': questions,
        'relations': relations,
        'sensitive_conditions': sensitive_conditions,
        'show_alert': True if inst_gp_user == cur_user else False,
        'patient_full_name': instruction.patient_information.get_full_name(),
        'library_form': library_form,
        'word_library': word_library,
        'library_history': library_history,
    })
    end_time = timezone.now()
    total_time = end_time - start_time
    logger.info("[RENDER XML] %s seconds with patient %s"%(total_time.seconds, instruction.patient_information.__str__()))
    return response


@login_required(login_url='/accounts/login')
@check_user_type(GENERAL_PRACTICE_USER)
def update_report(request: HttpRequest, instruction_id: str) -> HttpResponse:
    instruction = get_object_or_404(Instruction, id=instruction_id)
    if request.is_ajax():
        create_or_update_redaction_record(request, instruction)
        return JsonResponse({'message': 'Report has been saved.'})
    else:
        is_valid = create_or_update_redaction_record(request, instruction)
        if is_valid:
            if request.POST.get('event_flag') == 'submit':
                event_logger.info(
                    '{user}:{user_id} SUBMITTED medical report of instruction ID {instruction_id}'.format(
                        user=request.user, user_id=request.user.id,
                        instruction_id=instruction_id
                    )
                )
                if instruction.client_user:
                    calculate_instruction_fee(instruction)
                create_patient_report(request, instruction)
            if request.POST.get('event_flag') == 'preview':
                return redirect('medicalreport:submit_report', instruction_id=instruction_id)
            return redirect('instructions:view_pipeline')

    return redirect('medicalreport:edit_report', instruction_id=instruction_id)


#@silk_profile(name='Preview Report')
@login_required(login_url='/accounts/login')
def submit_report(request: HttpRequest, instruction_id: str) -> HttpResponse:
    header_title = "Preview and Submit Report"
    instruction = get_object_or_404(Instruction, id=instruction_id)
    redaction = get_object_or_404(AmendmentsForRecord, instruction=instruction_id)

    medical_record_decorator = MedicalReportDecorator(
        instruction.final_raw_medical_xml_report if instruction.final_raw_medical_xml_report else instruction.medical_xml_report.decode('utf-8'),
        instruction
    )
    attachments = medical_record_decorator.attachments
    relations = [relation.name for relation in ReferencePhrases.objects.all()]
    initial_prepared_by = request.user.userprofilebase.generalpracticeuser.pk
    if redaction.prepared_by:
        initial_prepared_by = redaction.prepared_by.pk
    finalise_submit_form = MedicalReportFinaliseSubmitForm(
        initial={
            'record_type': redaction.instruction.type,
            'SUBMIT_OPTION_CHOICES': (
                ('PREPARED_AND_REVIEWED', format_html(
                    'Signed off by <span id="preparer"></span>'.format(request.user.first_name)),
                 ),
            ),
            'prepared_by': initial_prepared_by,
            'prepared_and_signed': redaction.submit_choice or AmendmentsForRecord.PREPARED_AND_REVIEWED,
            'instruction_checked': redaction.instruction_checked
        },
        user=request.user)

    event_logger.info(
        '{user}:{user_id} ACCESS preview/submit of instruction ID {instruction_id}'.format(
            user=request.user, user_id=request.user.id,
            instruction_id=instruction_id
        )
    )

    gp_org = redaction.instruction.gp_user.organisation
    word_library = Library.objects.filter(gp_practice=gp_org)
    library_history = LibraryHistory.objects.filter(instruction=instruction)

    relations_dict = {
        'relations': relations,
        'word_library': word_library,
        'library_history': library_history,
    }

    return render(request, 'medicalreport/medicalreport_submit.html', {
        'header_title': header_title,
        'attachments': attachments,
        'redaction': redaction,
        'relations': relations_dict,
        'instruction': instruction,
        'finalise_submit_form': finalise_submit_form,
        'patient_full_name': instruction.patient_information.get_full_name()
    })


@login_required(login_url='/accounts/login')
def view_report(request: HttpRequest, instruction_id: str) -> HttpResponse:
    instruction = get_object_or_404(Instruction, id=instruction_id)
    return HttpResponse(
        instruction.medical_report if instruction.medical_report else bytes(instruction.medical_report_byte)
        , content_type='application/pdf')


@login_required(login_url='/accounts/login')
def view_consent_pdf(request: HttpRequest, instruction_id: str) -> HttpResponse:
    instruction = get_object_or_404(Instruction, id=instruction_id)
    return HttpResponse(instruction.mdx_consent, content_type='application/pdf')


def view_total_report(request: HttpRequest, instruction_id: str) -> HttpResponse:
    instruction = get_object_or_404(Instruction, id=instruction_id)

    return HttpResponse(instruction.medical_with_attachment_report,
                        content_type='application/pdf')


#@silk_profile(name='Final Report')
@login_required(login_url='/accounts/login')
@check_permission
def final_report(request: HttpRequest, instruction_id: str) -> HttpResponse:
    start_time = timezone.now()
    header_title = "Final Report"
    instruction = get_object_or_404(Instruction, id=instruction_id)
    redaction = get_object_or_404(AmendmentsForRecord, instruction=instruction_id)
    report_auth = get_object_or_404(PatientReportAuth, instruction=instruction_id)

    third_party = ThirdPartyAuthorisation.objects.filter(patient_report_auth=report_auth).first()
    if third_party:
        third_party_form = ConsentThirdParty(instance=third_party)
    else:
        third_party_form = ConsentThirdParty()

    patient_instruction = instruction.patient_information

    if request.POST:

        instruction.patient_notification = False
        instruction.third_party_notification = False

        if request.POST.get('send-to-patient'):
            instruction.patient_notification = True
            patient_instruction.patient_email = request.POST.get('patient_email', '')
            patient_instruction.patient_telephone_mobile = request.POST.get('patient_telephone_mobile', '')
            patient_instruction.patient_telephone_code = request.POST.get('patient_telephone_code', '')
            patient_instruction.save()

        if request.POST.get('send-to-third'):
            instruction.third_party_notification = True
            if third_party:
                third_party_form = ConsentThirdParty(request.POST, instance=third_party)
            else:
                third_party_form = ConsentThirdParty(request.POST)
            if third_party_form.is_valid():
                third_party = third_party_form.save(report_auth)

        instruction.save()

        send_report_notification(request, instruction, report_auth, third_party)

    patient_form = InstructionPatientForm(
        instance=patient_instruction,
        initial={
            'patient_title': patient_instruction.get_patient_title_display(),
            'patient_first_name': patient_instruction.patient_first_name,
            'patient_last_name': patient_instruction.patient_last_name,
            'patient_postcode': patient_instruction.patient_postcode,
            'patient_address_number': patient_instruction.patient_address_number,
            'patient_email': patient_instruction.patient_email,
            'confirm_email': patient_instruction.patient_email,
            'patient_telephone_mobile': patient_instruction.patient_telephone_mobile,
            'patient_dob': patient_instruction.patient_dob.strftime("%d/%m/%Y")
        }
    )

    # Todo REMOVE FILE SYSTEM SUPPORT
    if instruction.final_raw_medical_xml_report:
        final_raw_medical_xml_report = instruction.final_raw_medical_xml_report
    else:
        final_raw_medical_xml_report = instruction.medical_xml_report.read().decode('utf-8')
    medical_record_decorator = MedicalReportDecorator(final_raw_medical_xml_report, instruction)
    attachments = medical_record_decorator.attachments
    relations = [relation.name for relation in ReferencePhrases.objects.all()]
    has_patient_report_auth = True if instruction.patient_information.patient_email else False
    if instruction.patientreportauth_set.first():
        has_any_third_party_report_auth = True if instruction.patientreportauth_set.first().third_parties.first() else False
    else:
        has_any_third_party_report_auth = False
    patient_notification = instruction.patient_notification or has_patient_report_auth
    third_party_notification = has_any_third_party_report_auth

    response = render(request, 'medicalreport/final_report.html', {
        'header_title': header_title,
        'attachments': attachments,
        'redaction': redaction,
        'relations': relations,
        'third_party_form': third_party_form,
        'patient_form': patient_form,
        'instruction': instruction,
        'patient_notification': patient_notification,
        'third_party_notification': third_party_notification
    })
    end_time = timezone.now()
    total_time = end_time - start_time
    logger.info("[RENDER PDF] %s seconds with patient %s"%(total_time.seconds, instruction.patient_information.__str__()))
    event_logger.info(
        '{user}:{user_id} ACCESS final report view of instruction ID {instruction_id}'.format(
            user=request.user, user_id=request.user.id,
            instruction_id=instruction_id
        )
    )
    return response


@login_required(login_url='/accounts/login')
def trud_ivf(request: HttpRequest) -> HttpResponse:
    response = render(request, 'medicalreport/trud_ivf.html')
    return response


@login_required(login_url='/accounts/login')
def trud_std(request: HttpRequest) -> HttpResponse:
    response = render(request, 'medicalreport/trud_std.html')
    return response

@login_required(login_url='/accounts/login')
def trud_other(request: HttpRequest) -> HttpResponse:
    response = render(request, 'medicalreport/trud_other.html')
    return response
