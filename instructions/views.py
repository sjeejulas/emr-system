import ast
import json
import re
import pytz
import uuid
import requests
import dateutil
import logging

from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from common.functions import send_mail
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.http import HttpRequest, JsonResponse, HttpResponseRedirect
from django_tables2 import RequestConfig, Column
from django.views.decorators.cache import cache_page
from .models import Instruction, InstructionAdditionQuestion, InstructionConditionsOfInterest, Setting, InstructionPatient
from .tables import InstructionTable, FeeInstructionTable
from .model_choices import *
from .forms import ScopeInstructionForm, AdditionQuestionFormset, SarsConsentForm, MdxConsentForm,\
        ReferenceForm, ConsentForm, InstructionDateRangeForm, DateRangeSearchForm, ConsentThirdParty
from .tasks import prepare_medicalreport_data
from accounts.models import User, GeneralPracticeUser, PracticePreferences
from accounts.models import GENERAL_PRACTICE_USER, CLIENT_USER, MEDIDATA_USER
from accounts.forms import InstructionPatientForm, GPForm
from organisations.forms import GeneralPracticeForm
from organisations.models import OrganisationGeneralPractice, OrganisationClient
from organisations.views import get_gporganisation_data
from medicalreport.views import get_patient_registration
from medicalreport.models import AmendmentsForRecord
from common.functions import multi_getattr, get_url_page
from snomedct.models import SnomedConcept
from permissions.functions import check_permission
from .print_consents import MDXDualConsent
from report.models import ExceptionMerge, ThirdPartyAuthorisation, PatientReportAuth
from medicalreport.functions import create_patient_report
from template.models import TemplateInstruction
from payment.models import GpOrganisationFee
from payment.model_choices import FEE_STATUS_INVALID_DETAIL, FEE_STATUS_INVALID_FEE, FEE_STATUS_NOT_SETUP_ALL
#from silk.profiling.profiler import silk_profile

from datetime import timedelta
from itertools import chain
from typing import Dict, List


event_logger = logging.getLogger('medidata.event')

from django.conf import settings
PIPELINE_INSTRUCTION_LINK = get_url_page('instruction_pipeline')


def checkFeeStatus(gp_practice):
    org_fee = GpOrganisationFee.objects.filter(gp_practice=gp_practice).first()
    if org_fee:
        if not org_fee.organisation_fee:
            fee_setup_status = FEE_STATUS_INVALID_FEE
        elif org_fee.gp_practice.payment_bank_holder_name == '' or\
                org_fee.gp_practice.payment_bank_sort_code == '' or\
                org_fee.gp_practice.payment_bank_account_number == '':
            fee_setup_status = FEE_STATUS_INVALID_DETAIL
        else:
            fee_setup_status = None
    else:
        fee_setup_status = FEE_STATUS_NOT_SETUP_ALL
    return fee_setup_status


def count_instructions(user: User, gp_practice_code: str, client_organisation: OrganisationClient, page: str='') -> Dict[str, int]:
    naive = parse_datetime("2000-01-1 00:00:00")
    origin_date = pytz.timezone("Europe/London").localize(naive, is_dst=None)
    query_condition = Q(created__gt=origin_date)
    if user.type == GENERAL_PRACTICE_USER:
        if user.userprofilebase.generalpracticeuser.role == GeneralPracticeUser.PRACTICE_MANAGER:
            query_condition = Q(gp_practice_id=gp_practice_code)
        else:
            query_condition = Q(gp_practice_id=gp_practice_code) & (Q(gp_user=user.userprofilebase.generalpracticeuser) | Q(gp_user__isnull=True))
    elif user.type == CLIENT_USER:
        query_condition = Q(client_user__organisation=client_organisation)

    new_count = Instruction.objects.filter(query_condition, status=INSTRUCTION_STATUS_NEW).count()
    redacting_count = Instruction.objects.filter(query_condition, status=INSTRUCTION_STATUS_REDACTING).count()
    progress_count = Instruction.objects.filter(query_condition, status=INSTRUCTION_STATUS_PROGRESS).count()
    paid_count = Instruction.objects.filter(query_condition, status=INSTRUCTION_STATUS_PAID).count()
    complete_count = Instruction.objects.filter(query_condition, status=INSTRUCTION_STATUS_COMPLETE).count()
    rejected_count = Instruction.objects.filter(query_condition, status=INSTRUCTION_STATUS_REJECT).count()
    finalise_count = Instruction.objects.filter(query_condition, status=INSTRUCTION_STATUS_FINALISE).count()
    fail_count = Instruction.objects.filter(query_condition, status=INSTRUCTION_STATUS_RERUN).count()
    if page == 'pipeline_view':
        all_count = Instruction.objects.filter(query_condition).count()
        overall_instructions_number = {
            'All': all_count,
            'New': new_count,
            'Redacting': redacting_count,
            'In Progress': progress_count,
            'Paid': paid_count,
            'Completed': complete_count,
            'Rejected': rejected_count,
            'Finalising': finalise_count,
            'Rerun': fail_count,
        }
    elif page == 'fee_and_payment_pipeline':
        all_count = Instruction.objects.filter(query_condition, status__in=[INSTRUCTION_STATUS_PAID, INSTRUCTION_STATUS_COMPLETE]).count()
        overall_instructions_number = {
            'All': all_count,
            'Paid': paid_count,
            'Completed': complete_count,
        }
    else:
        overall_instructions_number = {}

    return overall_instructions_number


def count_fee_sensitive(gp_practice_code: str) -> Dict[str, int]:
    instruction_query_set = Instruction.objects.filter(type='AMRA')
    instruction_query_set = instruction_query_set.filter(gp_practice_id=gp_practice_code)

    # Count date = 3
    expected_date_3days = timezone.now() - timedelta(days=3)
    to_expected_date_3days = expected_date_3days.replace(hour=23, minute=59, second=59)
    from_expected_date_3days = expected_date_3days.replace(hour=00, minute=00, second=00)
    new_count_3days = instruction_query_set.filter(status=INSTRUCTION_STATUS_NEW, created__range=(from_expected_date_3days, to_expected_date_3days)).count()
    progess_count_3days = instruction_query_set.filter(status=INSTRUCTION_STATUS_PROGRESS, created__range=(from_expected_date_3days, to_expected_date_3days)).count()
    final_count_3days = instruction_query_set.filter(status=INSTRUCTION_STATUS_FINALISE, created__range=(from_expected_date_3days, to_expected_date_3days)).count()
    fail_count_3days = instruction_query_set.filter(status=INSTRUCTION_STATUS_RERUN, created__range=(from_expected_date_3days, to_expected_date_3days)).count()

    # Count date = 7
    expected_date_7days = timezone.now() - timedelta(days=7)
    to_expected_date_7days = expected_date_7days.replace(hour=23, minute=59, second=59)
    from_expected_date_7days = expected_date_7days.replace(hour=00, minute=00, second=00)
    new_count_7days = instruction_query_set.filter(status=INSTRUCTION_STATUS_NEW, created__range=(from_expected_date_7days, to_expected_date_7days)).count()
    progess_count_7days = instruction_query_set.filter(status=INSTRUCTION_STATUS_PROGRESS, created__range=(from_expected_date_7days, to_expected_date_7days)).count()
    final_count_7days = instruction_query_set.filter(status=INSTRUCTION_STATUS_FINALISE, created__range=(from_expected_date_7days, to_expected_date_7days)).count()
    fail_count_7days = instruction_query_set.filter(status=INSTRUCTION_STATUS_RERUN, created__range=(from_expected_date_7days, to_expected_date_7days)).count()

    # Count date = 11
    expected_date_11days = timezone.now() - timedelta(days=11)
    to_expected_date_11days = expected_date_11days.replace(hour=23, minute=59, second=59)
    from_expected_date_11days = expected_date_11days.replace(hour=00, minute=00, second=00)
    new_count_11days = instruction_query_set.filter(status=INSTRUCTION_STATUS_NEW, created__range=(from_expected_date_11days, to_expected_date_11days)).count()
    progess_count_11days = instruction_query_set.filter(status=INSTRUCTION_STATUS_PROGRESS, created__range=(from_expected_date_11days, to_expected_date_11days)).count()
    final_count_11days = instruction_query_set.filter(status=INSTRUCTION_STATUS_FINALISE, created__range=(from_expected_date_11days, to_expected_date_11days)).count()
    fail_count_11days = instruction_query_set.filter(status=INSTRUCTION_STATUS_RERUN, created__range=(from_expected_date_11days, to_expected_date_11days)).count()

    new_total_count = new_count_3days + new_count_7days + new_count_11days
    progress_total_count = progess_count_3days + progess_count_7days + progess_count_11days
    final_total_count = final_count_3days + final_count_7days + final_count_11days
    fail_total_count = fail_count_3days + fail_count_7days + fail_count_11days
    all_total_count = new_total_count + progress_total_count + final_total_count + fail_total_count

    fee_sensitive_number = {
        'All': all_total_count,
        'New': new_total_count,
        'In Progress': progress_total_count,
        'Finalising': final_total_count,
        'Rerun': fail_total_count
    }

    return fee_sensitive_number


def get_table_fee_sensitive(request: HttpRequest, gp_practice_code: str) -> InstructionTable:
    cost_column_name = 'Income £'
    instruction_query_set = Instruction.objects.filter(type='AMRA')
    instruction_query_set = instruction_query_set.filter(gp_practice_id=gp_practice_code)
    instruction_query_set = instruction_query_set.filter(~Q(status=INSTRUCTION_STATUS_COMPLETE) & ~Q(status=INSTRUCTION_STATUS_REJECT) & ~Q(status=INSTRUCTION_STATUS_PAID))

    table_number = request.GET.get('table', 1)
    if int(table_number) == 2:
        filter_status = request.GET.get('status', -1)
        if int(filter_status) != -1:
            instruction_query_set = instruction_query_set.filter(status=filter_status)

    # Get Value for table range 3 days.
    expected_date_3days = timezone.now() - timedelta(days=3)
    to_expected_date_3days = expected_date_3days.replace(hour=23, minute=59, second=59)
    from_expected_date_3days = expected_date_3days.replace(hour=00, minute=00, second=00)
    instruction_query_set_3days = Q(created__range=(from_expected_date_3days, to_expected_date_3days))

    # Get Value for table range 7 days.
    expected_date_7days = timezone.now() - timedelta(days=7)
    to_expected_date_7days = expected_date_7days.replace(hour=23, minute=59, second=59)
    from_expected_date_7days = expected_date_7days.replace(hour=00, minute=00, second=00)
    instruction_query_set_7days = Q(created__range=(from_expected_date_7days, to_expected_date_7days))

    # Get Value for table range 11 days.
    expected_date_11days = timezone.now() - timedelta(days=11)
    to_expected_date_11days = expected_date_11days.replace(hour=23, minute=59, second=59)
    from_expected_date_11days = expected_date_11days.replace(hour=00, minute=00, second=00)
    instruction_query_set_11days = Q(created__range=(from_expected_date_11days, to_expected_date_11days))

    instruction_query_set = instruction_query_set.filter(instruction_query_set_3days | instruction_query_set_7days | instruction_query_set_11days)
    table_fee = FeeInstructionTable(instruction_query_set, extra_columns=[('cost', Column(empty_values=(), verbose_name=cost_column_name))])
    table_fee.order_by = request.GET.get('sort', '-created')
    table_fee.paginate(page=request.GET.get('page_t2', 1), per_page=5)

    return table_fee


def count_model_search(request: HttpRequest, client_organisation: OrganisationClient=None, gp_practice_code: str=None) -> Dict[str, int]:
    search_input = request.GET.get('search')
    filter_type = request.GET.get('type', '')
    
    if filter_type and filter_type != 'allType':
        instruction_query_set = Instruction.objects.filter(type=filter_type)
    else:
        instruction_query_set = Instruction.objects.all()

    if request.user.type == CLIENT_USER:
        instruction_query_set = instruction_query_set.filter(client_user__organisation=client_organisation)
        instruction_query_set_client_ref = Q(your_ref__icontains=search_input)
        instruction_query_set_name = Q(patient_information__patient_first_name__icontains=search_input)
        instruction_query_set_last_name = Q(patient_information__patient_last_name__icontains=search_input)
        instruction_query_set = instruction_query_set.filter(Q(instruction_query_set_client_ref | instruction_query_set_name | instruction_query_set_last_name))
    else:
        instruction_query_set_name = Q(patient_information__patient_first_name__icontains=search_input)
        instruction_query_set_last_name = Q(patient_information__patient_last_name__icontains=search_input)
        instruction_query_set = instruction_query_set.filter(Q( instruction_query_set_name | instruction_query_set_last_name))
        instruction_query_set = instruction_query_set.filter(gp_practice_id=gp_practice_code)

    new_count = instruction_query_set.filter(status=INSTRUCTION_STATUS_NEW).count()
    progress_count = instruction_query_set.filter(status=INSTRUCTION_STATUS_PROGRESS).count()
    paid_count = instruction_query_set.filter(status=INSTRUCTION_STATUS_PAID).count()
    complete_count = instruction_query_set.filter(status=INSTRUCTION_STATUS_COMPLETE).count()
    rejected_count = instruction_query_set.filter(status=INSTRUCTION_STATUS_REJECT).count()
    finalise_count = instruction_query_set.filter(status=INSTRUCTION_STATUS_FINALISE).count()
    fail_count = instruction_query_set.filter(status=INSTRUCTION_STATUS_RERUN).count()
    all_count = new_count + progress_count + paid_count + complete_count + rejected_count + finalise_count + fail_count

    overall_instructions_number = {
        'All': all_count,
        'New': new_count,
        'In Progress': progress_count,
        'Paid': paid_count,
        'Completed': complete_count,
        'Rejected': rejected_count,
        'Finalising': finalise_count,
        'Rerun': fail_count,
    }

    return overall_instructions_number


def calculate_next_prev(page=None, **kwargs) -> Dict[str, str]:
    if not page:
        return {
            'next_disabled': 'disabled',
            'prev_disabled': 'disabled'
        }
    else:
        prev_disabled = ""
        next_disabled = ""
        if page.number <= 1:
            prev_page = 1
            prev_disabled = "disabled"
        else:
            prev_page = page.number - 1

        if page.number >= page.paginator.num_pages:
            next_disabled = "disabled"
            next_page = page.paginator.num_pages
        else:
            next_page = page.number + 1

        return {
            'next_page': next_page, 'prev_page': prev_page,
            'status': kwargs.get('filter_status'),
            'type': kwargs.get('filter_type'),
            'page_length': kwargs.get('page_length'),
            'next_disabled': next_disabled, 'prev_disabled': prev_disabled
        }


@login_required(login_url='/accounts/login')
def create_or_update_instruction(
        request, patient_instruction: InstructionPatient,
        scope_form: ScopeInstructionForm=None, date_range_form: InstructionDateRangeForm=None,
        gp_practice: OrganisationGeneralPractice=None, instruction_id: int=None
) -> Instruction:

    if instruction_id:
        instruction = get_object_or_404(Instruction, pk=instruction_id)
    else:
        instruction = Instruction()

        fee_data = GpOrganisationFee.objects.filter(gp_practice=gp_practice).first()
        if fee_data:
            instruction.ins_max_day_lvl_1 = fee_data.organisation_fee.max_day_lvl_1
            instruction.ins_max_day_lvl_2 = fee_data.organisation_fee.max_day_lvl_2
            instruction.ins_max_day_lvl_3 = fee_data.organisation_fee.max_day_lvl_3
            instruction.ins_max_day_lvl_4 = fee_data.organisation_fee.max_day_lvl_4
            instruction.ins_amount_rate_lvl_1 = fee_data.organisation_fee.amount_rate_lvl_1
            instruction.ins_amount_rate_lvl_2 = fee_data.organisation_fee.amount_rate_lvl_2
            instruction.ins_amount_rate_lvl_3 = fee_data.organisation_fee.amount_rate_lvl_3
            instruction.ins_amount_rate_lvl_4 = fee_data.organisation_fee.amount_rate_lvl_4

    if request.user.type == CLIENT_USER:
        instruction.client_user = request.user.userprofilebase.clientuser
        instruction.type = scope_form.cleaned_data['type']
        instruction.gp_practice = gp_practice
        instruction.consent_form = scope_form.cleaned_data['consent_form']
        instruction.gp_title_from_client = request.POST.get('gp_title')
        instruction.gp_initial_from_client = request.POST.get('initial')
        instruction.gp_last_name_from_client = request.POST.get('gp_last_name')
        from_date = scope_form.cleaned_data['date_range_from']
        to_date = scope_form.cleaned_data['date_range_to']
        if from_date or to_date:
            from_date = from_date if from_date else patient_instruction.patient_dob
            to_date = to_date if to_date else timezone.now()
        instruction.date_range_from = from_date
        instruction.date_range_to = to_date
    else:
        instruction.type = SARS_TYPE
        instruction.gp_practice = request.user.userprofilebase.generalpracticeuser.organisation
        instruction.gp_user = request.user.userprofilebase.generalpracticeuser
        from_date = date_range_form.cleaned_data['date_range_from']
        to_date = date_range_form.cleaned_data['date_range_to']
        if from_date or to_date:
            from_date = from_date if from_date else patient_instruction.patient_dob
            to_date = to_date if to_date else timezone.now()
        instruction.date_range_from = from_date
        instruction.date_range_to = to_date

    instruction.type_catagory = request.POST.get('type_catagory', 3)
    instruction.patient_information_id = patient_instruction.id
    instruction.save()

    return instruction


def create_addition_question(instruction: Instruction, addition_question_formset: AdditionQuestionFormset) -> None:
    for form in addition_question_formset:
        if form.is_valid() and form.cleaned_data:
            addition_question = form.save(commit=False)
            addition_question.instruction = instruction
            addition_question.save()


def create_snomed_relations(instruction: Instruction, condition_of_interests: List[str]) -> None:
    for condition_code in condition_of_interests:
        snomedct = SnomedConcept.objects.filter(external_id=condition_code)
        if snomedct.exists():
            snomedct = snomedct.first()
            InstructionConditionsOfInterest.objects.create(instruction=instruction, snomedct=snomedct)


#@silk_profile(name='Pipline View')
@login_required(login_url='/accounts/login')
def instruction_pipeline_view(request):
    event_logger.info(
        '{user}:{user_id} ACCESS instruction pipeline view'.format(user=request.user, user_id=request.user.id)
    )
    gp_practice_code = multi_getattr(request, 'user.userprofilebase.generalpracticeuser.organisation.pk', default=None)
    header_title = "Instructions Pipeline"
    user = request.user
    table_num = request.GET.get('table', 'undefined')
    search_input = request.GET.get('search', None)
    search_status = False
    search_pagination = None
    table_fee = None
    next_prev_data_all = {}
    next_prev_data_fee = {}
    check_fee_status = None

    if table_num == 'undefined':
        table_num = 1

    if user.type == GENERAL_PRACTICE_USER:
        gp_practice = multi_getattr(request, 'user.userprofilebase.generalpracticeuser.organisation', default=None)
        if request.user.has_perm('instructions.view_account_pages'):
            check_fee_status = checkFeeStatus(gp_practice)

        if gp_practice and not gp_practice.is_active():
            return redirect('onboarding:step3', practice_code=gp_practice.pk)

        table_fee = get_table_fee_sensitive(request, gp_practice_code)

    if 'status' in request.GET:
        filter_type = request.GET.get('type', '')
        filter_status = request.GET.get('status', -1)
        if filter_status == 'undefined':
            filter_status = -1
        else:
            filter_status = int(filter_status)

        if filter_type == 'undefined':
            filter_type = 'allType'
    else:
        filter_type = request.COOKIES.get('type', '')
        filter_status = int(request.COOKIES.get('status', -1))

    if filter_type and filter_type != 'allType':
        instruction_query_set = Instruction.objects.filter(type=filter_type)
    else:
        instruction_query_set = Instruction.objects.all()

    if table_num != 2:
        if filter_status != -1:
            instruction_query_set = instruction_query_set.filter(status=filter_status)

    client_organisation = multi_getattr(request, 'user.userprofilebase.clientuser.organisation', default=None)
    overall_instructions_number = count_instructions(request.user, gp_practice_code, client_organisation, 'pipeline_view')
    count_fee_sensitive_number = count_fee_sensitive(gp_practice_code)
    cost_column_name = 'Fee £'
    if request.user.type == CLIENT_USER:
        cost_column_name = 'Cost £'
        instruction_query_set = instruction_query_set.filter(client_user__organisation=client_organisation)
        if search_input:
            instruction_query_set_client_ref = Q(your_ref__icontains=search_input)
            instruction_query_set_name = Q(patient_information__patient_first_name__icontains=search_input)
            instruction_query_set_last_name = Q(patient_information__patient_last_name__icontains=search_input)
            instruction_query_set = instruction_query_set.filter(instruction_query_set_client_ref | instruction_query_set_name | instruction_query_set_last_name)
            overall_instructions_number = count_model_search(request, client_organisation=client_organisation)
            search_status = True

    if request.user.type == GENERAL_PRACTICE_USER:
        cost_column_name = 'Income £'
        instruction_query_set = instruction_query_set.filter(gp_practice_id=gp_practice_code)
        
        if search_input:
            instruction_query_set_name = Q(patient_information__patient_first_name__icontains=search_input)
            instruction_query_set_last_name = Q(patient_information__patient_last_name__icontains=search_input)
            instruction_query_set = instruction_query_set.filter(instruction_query_set_name | instruction_query_set_last_name)
            overall_instructions_number = count_model_search(request, gp_practice_code=gp_practice_code)
            search_status = True

    if search_status:
        table_all = InstructionTable(instruction_query_set, extra_columns=[('cost', Column(empty_values=(), verbose_name=cost_column_name))])
        table_all.order_by = request.GET.get('sort', '-created')
        table_all.paginate(page=request.GET.get('page_ts', 1), per_page=5)
        search_pagination = 'search'
    else:
        table_all = InstructionTable(instruction_query_set, extra_columns=[('cost', Column(empty_values=(), verbose_name=cost_column_name))])
        table_all.order_by = request.GET.get('sort', '-created')
        RequestConfig(request, paginate={'per_page': 5}).configure(table_all)

    if table_all:
        next_prev_data_all = calculate_next_prev(table_all.page, filter_status=filter_status, filter_type=filter_type)

    if table_fee:
        next_prev_data_fee = calculate_next_prev(table_fee.page, filter_status=filter_status, filter_type=filter_type)

    response = render(request, 'instructions/pipeline_views_instruction.html', {
        'user': user,
        'table_all': table_all,
        'table_fee': table_fee,
        'overall_instructions_number': overall_instructions_number,
        'count_fee_sensitive_number': count_fee_sensitive_number,
        'header_title': header_title,
        'next_prev_data_all': next_prev_data_all,
        'next_prev_data_fee': next_prev_data_fee,
        'check_fee_status': check_fee_status,
        'search_pagination': search_pagination,
        'search_input': search_input
    })

    response.set_cookie('status', filter_status)
    response.set_cookie('type', filter_type)
    return response


@login_required(login_url='/accounts/login')
def instruction_invoice_payment_view(request):
    # comment
    event_logger.info(
        '{user}:{user_id} ACCESS Invoicing and Payments pipeline view'.format(user=request.user, user_id=request.user.id)
    )
    header_title = "Invoicing and Payments"
    user = request.user
    date_range_form = DateRangeSearchForm()

    if user.type == GENERAL_PRACTICE_USER:
        gp_practice = multi_getattr(request, 'user.userprofilebase.generalpracticeuser.organisation', default=None)
        if gp_practice and not gp_practice.is_active():
            return redirect('onboarding:step3', practice_code=gp_practice.pk)

    filter_type = ''
    filter_status = -1
    if 'status' in request.GET:
        filter_type = request.GET.get('type', '')
        filter_status = request.GET.get('status', -1)
        if filter_status == 'undefined':
            filter_status = -1
        else:
            filter_status = int(filter_status)

        if filter_type == 'undefined':
            filter_type = 'allType'

    if filter_type and filter_type != 'allType':
        instruction_query_set = Instruction.objects.filter(type=filter_type, status__in=[INSTRUCTION_STATUS_COMPLETE, INSTRUCTION_STATUS_PAID])
    else:
        instruction_query_set = Instruction.objects.filter(status__in=[INSTRUCTION_STATUS_COMPLETE, INSTRUCTION_STATUS_PAID])

    if filter_status != -1:
        instruction_query_set = instruction_query_set.filter(status=filter_status)

    gp_practice_code = multi_getattr(request, 'user.userprofilebase.generalpracticeuser.organisation.pk', default=None)
    client_organisation = multi_getattr(request, 'user.userprofilebase.clientuser.organisation', default=None)
    overall_instructions_number = count_instructions(request.user, gp_practice_code, client_organisation, page='fee_and_payment_pipeline')
    cost_column_name = 'Fee £'
    if request.user.type == CLIENT_USER:
        cost_column_name = 'Cost £'
        instruction_query_set = instruction_query_set.filter(client_user__organisation=client_organisation)

    if request.user.type == GENERAL_PRACTICE_USER:
        cost_column_name = 'Income £'
        instruction_query_set = instruction_query_set.filter(gp_practice_id=gp_practice_code)

    if request.method == 'POST':
        if request.POST.get('from_date', '') and request.POST.get('to_date', ''):
            from_date = dateutil.parser.parse(request.POST.get('from_date', '')).replace(tzinfo=pytz.UTC)
            to_date = dateutil.parser.parse(request.POST.get('to_date', '')).replace(tzinfo=pytz.UTC)
            instruction_query_set = instruction_query_set.filter(completed_signed_off_timestamp__range=[from_date, to_date])

    table = InstructionTable(instruction_query_set, extra_columns=[
        ('cost', Column(empty_values=(), verbose_name=cost_column_name)),
        ('fee_note', Column(empty_values=(), verbose_name='Fee Note', default='---'))
    ])
    table.order_by = request.GET.get('sort', 'status')
    RequestConfig(request, paginate={'per_page': 5}).configure(table)

    response = render(request, 'instructions/invoice_payment_pipline_view_instructions.html', {
        'user': user,
        'table': table,
        'overall_instructions_number': overall_instructions_number,
        'header_title': header_title,
        'next_prev_data': calculate_next_prev(table.page, filter_status=filter_status, filter_type=filter_type),
        'date_range_form': date_range_form,
    })

    return response


#@silk_profile(name='New Instruction')
@login_required(login_url='/accounts/login')
@check_permission
def new_instruction(request):
    header_title = "Add New Instruction"
    gp_form = GPForm()
    nhs_form = GeneralPracticeForm()
    reference_form = ReferenceForm()
    date_range_form = InstructionDateRangeForm()
    client_organisation = multi_getattr(request.user, 'userprofilebase.clientuser.organisation', default=None)
    if client_organisation:
        templates = TemplateInstruction.objects.filter(Q(organisation=client_organisation) | Q(organisation__isnull=True))
    else:
        templates = TemplateInstruction.objects.filter(organisation__isnull=True)

    if request.method == "POST":
        request.POST._mutable = True
        instruction_id = request.POST.get('instruction_id', None)
        gp_form = GPForm(request.POST)
        addition_question_formset = AdditionQuestionFormset(request.POST)
        raw_common_condition = request.POST.getlist('common_condition')
        common_condition_list = list(chain.from_iterable([ast.literal_eval(item) for item in raw_common_condition]))
        addition_condition_list = request.POST.getlist('addition_condition')
        condition_of_interests = list(set().union(common_condition_list, addition_condition_list))
        scope_form = ScopeInstructionForm(request.user, request.POST.get('patient_email'), request.POST, request.FILES)
        selected_pat_code = request.POST.get('patient_postcode', '')
        selected_pat_adr_num = request.POST.get('patient_address_number', '')
        selected_gp_code = request.POST.get('gp_practice', '')
        selected_gp_name = request.POST.get('gp_practice_name', '')
        selected_add_cond = request.POST.getlist('addition_condition', [])
        selected_add_cond_title = request.POST.get('addition_condition_title', '')
        selected_add_cond_title = selected_add_cond_title.split(',')
        selected_gp_adr_line1 = request.POST.get('patient_address_line1', '')
        selected_gp_adr_line2 = request.POST.get('patient_address_line2', '')
        selected_gp_adr_line3 = request.POST.get('patient_address_line3', '')
        selected_gp_adr_county = request.POST.get('patient_county', '')
        patient_form = InstructionPatientForm(InstructionPatientForm.change_request_date(request.POST))
        date_range_form = InstructionDateRangeForm(request.POST)

        i = 0
        while i < len(selected_add_cond):
            selected_add_cond[i] = int(selected_add_cond[i])
            i += 1

        # Is from NHS or gpOrganisation
        gp_practice_code = request.POST.get('gp_practice', None)
        if not gp_practice_code:
            gp_practice_code = multi_getattr(request, 'user.userprofilebase.generalpracticeuser.organisation.pk', default=None)
        gp_practice = OrganisationGeneralPractice.objects.filter(practcode=gp_practice_code).first()
        if (patient_form.is_valid() and scope_form.is_valid() and gp_practice) or\
                (request.user.type == GENERAL_PRACTICE_USER and patient_form.is_valid()\
                and date_range_form.is_valid()):
            if instruction_id:
                prev_instruction = get_object_or_404(Instruction, pk=instruction_id)
                patient_instruction = get_object_or_404(InstructionPatient, instruction=prev_instruction)
                patient_instruction_form = InstructionPatientForm(request.POST, instance=patient_instruction)
                if patient_instruction_form.is_valid():
                    patient_instruction_form.save()
            else:
                patient_instruction = patient_form.save()
            # create instruction
            instruction = create_or_update_instruction(
                request=request, patient_instruction=patient_instruction,
                scope_form=scope_form, date_range_form=date_range_form,
                gp_practice=gp_practice, instruction_id=instruction_id
            )
            reference_form = ReferenceForm(request.POST, instance=instruction)
            if reference_form.is_valid():
                reference_form.save()
            practice_preferences = PracticePreferences.objects.get_or_create(gp_organisation=gp_practice)
            if practice_preferences[0].notification == 'NEW':
                send_mail(
                    'New Instruction',
                    'You have a new instruction. Click here {protocol}://{link} to view.'.format(
                        protocol=request.scheme,
                        link=request.get_host() + reverse('instructions:view_pipeline')
                    ),
                    'MediData',
                    [gp_practice.organisation_email],
                    fail_silently=True,
                )
            if request.user.type == CLIENT_USER:
                # create relations of instruction with snomed code
                create_snomed_relations(instruction, condition_of_interests)
                # create addition question
                create_addition_question(instruction, addition_question_formset)
            else:
                send_mail(
                    'New Instruction',
                    'Your instruction has been created',
                    'MediData',
                    [patient_form.cleaned_data['patient_email']],
                    fail_silently=True,
                )

            if instruction.type == AMRA_TYPE and not instruction.consent_form:
                message = 'Your instruction requires a consent form. Please sign and upload or accept terms of consent here {protocol}://{link}'\
                    .format(
                        protocol=request.scheme,
                        link=request.get_host() + '/instruction/upload-consent/' + str(instruction.id) + '/'
                    )
                send_mail(
                    'Consent Request',
                    message,
                    'MediData',
                    [patient_form.cleaned_data['patient_email']],
                    fail_silently=True,
                )

            medidata_emails_list = [user.email for user in User.objects.filter(type=MEDIDATA_USER)]
            gp_emails_list = []
            # Notification: client selected NHS GP
            if not gp_practice.live and not gp_practice.accept_policy:
                send_mail(
                    'Non enabled GP Surgery',
                    'Your client has selected: {GP_Surgery_Details}'.format(GP_Surgery_Details=gp_practice.name),
                    'MediData',
                    medidata_emails_list,
                    fail_silently=True,
                )
            else:
                gp_emails_list = [gp.user.email for gp in GeneralPracticeUser.objects.filter(organisation=gp_practice)]

            # Notification: client created new instruction
            if settings.NEW_INSTRUCTION_SEND_MAIL_TO_MEDI:
                send_mail(
                    'New Instruction',
                    'You have a new instruction. Click here {protocol}://{link} to see it.'.format(
                        protocol=request.scheme,
                        link=request.get_host() + reverse('instructions:view_pipeline')
                    ),
                    'MediData',
                    medidata_emails_list + gp_emails_list,
                    fail_silently=True,
                )
                
            messages.success(request, 'Form submission successful')
            event_logger.info(
                '{user}:{user_id} {action} {instruction_type} instruction'.format(
                    user=request.user, user_id=request.user.id,
                    action='CREATED' if not instruction_id else 'EDITED',
                    instruction_type=instruction.type,
                )
            )
            if instruction.type == SARS_TYPE and request.user.type == GENERAL_PRACTICE_USER:
                return redirect('medicalreport:set_patient_emis_number', instruction_id=instruction.id)
            else:
                return redirect('instructions:view_pipeline')
        else:
            return render(request, 'instructions/new_instruction.html', {
                'header_title': header_title,
                'patient_form': patient_form,
                'nhs_form': nhs_form,
                'gp_form': gp_form,
                'scope_form': scope_form,
                'templates': templates,
                'date_range_form': date_range_form,
                'reference_form': reference_form,
                'addition_question_formset': addition_question_formset,
                'selected_pat_code': selected_pat_code,
                'selected_pat_adr_num': selected_pat_adr_num,
                'selected_gp_code': selected_gp_code,
                'selected_gp_name': selected_gp_name,
                'selected_add_cond': selected_add_cond,
                'selected_add_cond_title': json.dumps(selected_add_cond_title),
                'selected_gp_adr_line1': selected_gp_adr_line1,
                'selected_gp_adr_line2': selected_gp_adr_line2,
                'selected_gp_adr_line3': selected_gp_adr_line3,
                'selected_gp_adr_county': selected_gp_adr_county
            })
    patient_form = InstructionPatientForm()
    addition_question_formset = AdditionQuestionFormset(queryset=InstructionAdditionQuestion.objects.none())
    scope_form = ScopeInstructionForm(user=request.user)

    instruction_id = request.GET.get('instruction_id', None)
    if instruction_id:
        instruction = get_object_or_404(Instruction, pk=instruction_id)
        patient_instruction = instruction.patient_information
        gp_organisation = instruction.gp_practice
        
        # Initial GP Practice Block
        gp_address = ' '.join(
            (
                gp_organisation.region,
                gp_organisation.comm_area,
                gp_organisation.billing_address_street,
                gp_organisation.billing_address_city,
                gp_organisation.billing_address_state,
                gp_organisation.billing_address_postalcode,
            )
        )
        if gp_organisation.live:
            gp_status = 'live surgery'
            gp_status_class = 'text-success'
        else:
            if gp_organisation.gp_operating_system == 'EMISWeb':
                gp_status = 'Access not set-up'
                gp_status_class = 'text-danger'
            else:
                gp_status = 'Not applicable'
                gp_status_class = 'text-dark'
        

        # Initial Patient Form
        patient_form = InstructionPatientForm(
            instance=patient_instruction,
            initial={
                'first_name': patient_instruction.patient_first_name,
                'last_name': patient_instruction.patient_last_name,
                'address_postcode': patient_instruction.patient_postcode,
                'patient_postcode': patient_instruction.patient_postcode,
                'patient_address_number': patient_instruction.patient_address_number,
                'edit_patient': True
            }
        )
        # Initial GP/NHS Organisation Form
        if isinstance(instruction.gp_practice, OrganisationGeneralPractice):
            gp_practice_code = instruction.gp_practice.practcode
        else:
            gp_practice_code = instruction.gp_practice.pk
        gp_practice_request = HttpRequest()
        gp_practice_request.GET['code'] = gp_practice_code
        nhs_address = get_gporganisation_data(gp_practice_request, need_dict=True)['address']
        nhs_form = GeneralPracticeForm()
        # Initial GP Practitioner Form
        gp_form = GPForm(
            initial={
                'gp_title': instruction.gp_title_from_client,
                'initial': instruction.gp_initial_from_client,
                'gp_last_name': instruction.gp_last_name_from_client,
            }
        )
        # Initial Scope/Consent Form
        scope_form = ScopeInstructionForm(user=request.user, initial={'type': instruction.type, })

        consent_type = 'pdf'
        consent_extension = ''
        consent_path = ''
        if instruction.consent_form:
            consent_extension = (instruction.consent_form.url).split('.')[1]
            consent_path = instruction.consent_form.url
        if consent_extension in ['jpeg', 'png', 'gif']:
            consent_type = 'image'
        consent_form_data = {
            'type': consent_type,
            'path': consent_path
        }

        condition_of_interest = [snomed.fsn_description for snomed in instruction.selected_snomed_concepts()]
        addition_question_formset = AdditionQuestionFormset(queryset=InstructionAdditionQuestion.objects.filter(instruction=instruction))

        return render(request, 'instructions/new_instruction.html', {
            'header_title': header_title,
            'patient_form': patient_form,
            'nhs_form': nhs_form,
            'gp_form': gp_form,
            'scope_form': scope_form,
            'templates': templates,
            'date_range_form': date_range_form,
            'addition_question_formset': addition_question_formset,
            'nhs_address': nhs_address,
            'condition_of_interest': condition_of_interest,
            'consent_form_data': consent_form_data,
            'instruction_id': instruction_id,
            'reference_form': reference_form,
            'patient_postcode': patient_instruction.patient_postcode,
            'selected_pat_adr_num': patient_instruction.patient_address_number,
            'selected_gp_adr_line1': patient_instruction.patient_address_line1,
            'selected_gp_adr_line2': patient_instruction.patient_address_line2,
            'selected_gp_adr_line3': patient_instruction.patient_address_line3,
            'selected_gp_adr_county': patient_instruction.patient_county,
            'selected_gp_code': gp_organisation,
            'gp_address': gp_address,
            'gp_status': gp_status,
            'gp_status_class': gp_status_class
        })
    event_logger.info(
        '{user}:{user_id} ACCESS NEW instruction view'.format(
            user=request.user, user_id=request.user.id,
        )
    )
    return render(request, 'instructions/new_instruction.html', {
        'header_title': header_title,
        'patient_form': patient_form,
        'nhs_form': nhs_form,
        'gp_form': gp_form,
        'scope_form': scope_form,
        'templates': templates,
        'date_range_form': date_range_form,
        'reference_form': reference_form,
        'addition_question_formset': addition_question_formset
    })


def upload_consent(request, instruction_id):
    setting = Setting.objects.all().first()
    instruction = get_object_or_404(Instruction, pk=instruction_id)
    consent_form = ConsentForm()
    uploaded = False
    select_type = ''
    if instruction.status != INSTRUCTION_STATUS_NEW:
        uploaded = True
    if request.method == "POST" and setting:
        if request.POST.get('select_type') == 'accept':
            instruction.consent_form = setting.consent_form
            select_type = 'accept'
            instruction.save()
            uploaded = True
        else:
            consent_form = ConsentForm(request.POST, request.FILES, instance=instruction)
            if consent_form.is_valid():
                consent_form.save()
                uploaded = True
            select_type = 'upload'
    return render(request, 'instructions/upload_consent.html', {
            'instruction': instruction,
            'consent_form': consent_form,
            'setting': setting,
            'uploaded': uploaded,
            'select_type': select_type
        })


@login_required(login_url='/accounts/login')
def update_gp_allocated_user(request):
    instruction = get_object_or_404(
        Instruction, pk=request.POST['instruction_id'])
    payload_gp_user = get_object_or_404(
        GeneralPracticeUser, pk=request.POST['selected_gp_id'])

    instruction.gp_user = payload_gp_user
    instruction.save()

    return redirect('accounts:view_users')


#@silk_profile(name='Review Instruction')
@login_required(login_url='/accounts/login')
@check_permission
def review_instruction(request, instruction_id: str):
    header_title = "Instruction Reviewing"
    instruction = get_object_or_404(Instruction, pk=instruction_id)
    patient_instruction = instruction.patient_information
    date_format = patient_instruction.patient_dob.strftime("%d/%m/%Y")
    date_range_form = InstructionDateRangeForm(instance=instruction)

    if request.method == "POST":
        instruction.reject(request, request.POST)
        event_logger.info(
            '{user}:{user_id} REJECT instruction ID {instruction_id} on failed'.format(
                user=request.user, user_id=request.user.id,
                instruction_id=instruction_id
            )
        )
        return HttpResponseRedirect("%s?%s"%(reverse('instructions:view_pipeline'),"status=%s&type=allType"%INSTRUCTION_STATUS_REJECT))            

    # Initial Patient Form
    patient_form = InstructionPatientForm(
        instance=patient_instruction,
        initial={
            'patient_title': patient_instruction.get_patient_title_display(),
            'patient_first_name': patient_instruction.patient_first_name,
            'patient_last_name': patient_instruction.patient_last_name,
            'patient_postcode': patient_instruction.patient_postcode,
            'patient_address_number': patient_instruction.patient_address_number,
            'patient_dob': date_format
        }
    )
    # 
    gp_practice_code = instruction.gp_practice.pk
    gp_practice_request = HttpRequest()
    gp_practice_request.GET['code'] = gp_practice_code
    gp_organisation_address = get_gporganisation_data(gp_practice_request, need_dict=True)['address']
    reference_form = ReferenceForm(instance=instruction)
    nhs_form = GeneralPracticeForm(
        initial={
            'gp_practice': instruction.gp_practice
        }
    )
    # Initial GP Practitioner Form
    gp_form = GPForm(
        initial={
            'gp_title': instruction.gp_title_from_client,
            'initial': instruction.gp_initial_from_client,
            'gp_last_name': instruction.gp_last_name_from_client,
        }
    )
    # Initial Scope/Consent Form
    scope_form = ScopeInstructionForm(user=request.user, initial={'type': instruction.type, })

    consent_type = 'pdf'
    consent_extension = ''
    consent_path = ''
    if instruction.consent_form:
        consent_extension = (instruction.consent_form.url).split('.')[-1]
        consent_path = instruction.consent_form.url
    if consent_extension in ['jpeg', 'png', 'gif']:
        consent_type = 'image'
    consent_form_data = {
        'type': consent_type,
        'path': consent_path
    }

    condition_of_interest = [snomed.fsn_description for snomed in instruction.selected_snomed_concepts()]
    addition_question_formset = AdditionQuestionFormset(queryset=InstructionAdditionQuestion.objects.filter(instruction=instruction))

    can_process = False
    if request.user.has_perm('instructions.process_sars') and instruction.type == 'SARS':
        can_process = True
    elif request.user.has_perm('instructions.process_amra') and instruction.type == 'AMRA':
        can_process = True

    event_logger.info(
        '{user}:{user_id} ACCESS REVIEW instruction ID {instruction_id}'.format(
            user=request.user, user_id=request.user.id,
            instruction_id=instruction_id
        )
    )

    return render(request, 'instructions/review_instruction.html', {
        'header_title': header_title,
        'patient_form': patient_form,
        'nhs_form': nhs_form,
        'gp_form': gp_form,
        'scope_form': scope_form,
        'date_range_form': date_range_form,
        'reference_form': reference_form,
        'addition_question_formset': addition_question_formset,
        'nhs_address': gp_organisation_address,
        'condition_of_interest': condition_of_interest,
        'consent_form_data': consent_form_data,
        'instruction_id': instruction_id,
        'instruction': instruction,
        'can_process': can_process,
        'reject_reason_value': CANCEL_BY_CLIENT,
    })


#@silk_profile(name='View Reject')
@cache_page(300)
@login_required(login_url='/accounts/login')
@check_permission
def view_reject(request, instruction_id: str):
    instruction = get_object_or_404(Instruction, pk=instruction_id)
    patient_instruction = instruction.patient_information
    # Initial Patient Form
    patient_form = InstructionPatientForm(
        instance=patient_instruction,
        initial={
            'patient_title': patient_instruction.get_patient_title_display(),
            'patient_first_name': patient_instruction.patient_first_name,
            'patient_last_name': patient_instruction.patient_last_name,
            'patient_postcode': patient_instruction.patient_postcode,
            'patient_address_number': patient_instruction.patient_address_number,
        }
    )
    gp_practice_code = instruction.gp_practice.pk
    gp_practice_request = HttpRequest()
    gp_practice_request.GET['code'] = gp_practice_code
    nhs_address = get_gporganisation_data(gp_practice_request, need_dict=True)['address']
    nhs_form = GeneralPracticeForm(
        initial={
            'gp_practice': instruction.gp_practice
        }
    )
    # Initial GP Practitioner Form
    gp_form = GPForm(
        initial={
            'gp_title': instruction.gp_title_from_client,
            'initial': instruction.gp_initial_from_client,
            'gp_last_name': instruction.gp_last_name_from_client,
        }
    )
    # Initial Scope/Consent Form
    scope_form = ScopeInstructionForm(user=request.user, initial={'type': instruction.type, })
    reference_form = ReferenceForm(instance=instruction)

    consent_type = 'pdf'
    consent_extension = ''
    consent_path = ''
    if instruction.consent_form:
        consent_extension = (instruction.consent_form.url).split('.')[1]
        consent_path = instruction.consent_form.url
    if consent_extension in ['jpeg', 'png', 'gif']:
        consent_type = 'image'
    consent_form_data = {
        'type': consent_type,
        'path': consent_path
    }

    condition_of_interest = [snomed.fsn_description for snomed in instruction.selected_snomed_concepts()]
    addition_question_formset = AdditionQuestionFormset(queryset=InstructionAdditionQuestion.objects.filter(instruction=instruction))

    event_logger.info(
        '{user}:{user_id} ACCESS REJECT view instruction ID {instruction_id} view'.format(
            user=request.user, user_id=request.user.id,
            instruction_id=instruction_id
        )
    )

    return render(request, 'instructions/view_reject.html', {
        'patient_form': patient_form,
        'nhs_form': nhs_form,
        'gp_form': gp_form,
        'scope_form': scope_form,
        'reference_form': reference_form,
        'addition_question_formset': addition_question_formset,
        'nhs_address': nhs_address,
        'condition_of_interest': condition_of_interest,
        'consent_form_data': consent_form_data,
        'instruction': instruction,
        'instruction_id': instruction.id,
    })


@login_required(login_url='/accounts/login')
def view_fail(request, instruction_id: str):
    instruction = get_object_or_404(Instruction, pk=instruction_id)

    if request.method == "POST":
        if request.POST.get('next_step') == 'Reject':
            instruction.reject(request, request.POST)
            event_logger.info(
                '{user}:{user_id} REJECT instruction ID {instruction_id} on failed'.format(
                    user=request.user, user_id=request.user.id,
                    instruction_id=instruction_id
                )
            )
            return HttpResponseRedirect("%s?%s"%(reverse('instructions:view_pipeline'),"status=%s&type=allType"%INSTRUCTION_STATUS_REJECT))
        elif request.POST.get('next_step') == 'Edit':
            instruction.status = INSTRUCTION_STATUS_PROGRESS
            instruction.save()
            return redirect('medicalreport:edit_report', instruction_id=instruction_id)
        elif request.POST.get('next_step') == 'Retry':
            create_patient_report(request, instruction)
            instruction.status = INSTRUCTION_STATUS_FINALISE
            instruction.save()
            event_logger.info(
                '{user}:{user_id} RETRY celery task instruction ID {instruction_id}'.format(
                    user=request.user, user_id=request.user.id,
                    instruction_id=instruction_id
                )
            )
            return redirect('instructions:view_pipeline')

    exception_merge = ExceptionMerge.objects.filter(instruction=instruction).first()

    event_logger.info(
        '{user}:{user_id} ACCESS FAILED view instruction ID {instruction_id}'.format(
            user=request.user, user_id=request.user.id,
            instruction_id=instruction_id
        )
    )

    return render(request, 'instructions/view_fail.html', {
        'instruction': instruction,
        'reject_reason_value': GENERATOR_FAIL,
        'exception_merge': exception_merge
    })


#@silk_profile(name='Consent Contact View')
@login_required(login_url='/accounts/login')
@check_permission
def consent_contact(request, instruction_id, patient_emis_number):
    instruction = get_object_or_404(Instruction, pk=instruction_id)
    report_auth = PatientReportAuth.objects.filter(instruction=instruction).first()
    patient_instruction = instruction.patient_information
    mdx_consent_form = MdxConsentForm()
    patient_registration = get_patient_registration(str(patient_emis_number), gp_organisation=instruction.gp_practice)

    if report_auth:
        third_party = ThirdPartyAuthorisation.objects.filter(patient_report_auth=report_auth).first()
        third_party_form = ConsentThirdParty(instance=third_party)
    else:
        third_party_form = ConsentThirdParty()

    if isinstance(patient_registration, HttpResponseRedirect):
        return patient_registration

    if request.method == "POST":
        # Synchronous preparing task case
        mdx_consent_form = MdxConsentForm(request.POST, request.FILES, instance=instruction)
        if request.POST.get('mdx_consent_loaded') == 'loaded' and mdx_consent_form.is_valid():
            mdx_consent_form.save()
        elif request.POST.get('mdx_consent_loaded') != 'loaded':
            instruction.mdx_consent.delete()

        patient_email = request.POST.get('patient_email', '')
        patient_telephone_mobile = request.POST.get('patient_telephone_mobile', '')

        if request.POST.get('send-to-patient'):
            instruction.patient_notification = True
        if request.POST.get('send-to-third'):
            instruction.third_party_notification = True
            if not PatientReportAuth.objects.filter(instruction=instruction):
                unique_url = uuid.uuid4().hex
                PatientReportAuth.objects.create(patient=instruction.patient, instruction=instruction, url=unique_url)

            report_auth = get_object_or_404(PatientReportAuth, instruction=instruction)
            third_party = ThirdPartyAuthorisation.objects.filter(patient_report_auth=report_auth).first()
            if third_party:
                third_party_form = ConsentThirdParty(request.POST, instance=third_party)
            else:
                third_party_form = ConsentThirdParty(request.POST)

            if third_party_form.is_valid():
                third_party_authorisation = third_party_form.save(report_auth)
                event_logger.info('CREATED third party authorised model ID {model_id}'.format(
                    model_id=third_party_authorisation.id)
                )

        if request.POST.get('mdx_consent_loaded') != 'loaded' or mdx_consent_form.is_valid():
            patient_instruction.patient_email = patient_email
            patient_instruction.patient_telephone_mobile = patient_telephone_mobile
            patient_instruction.patient_telephone_code = request.POST.get('patient_telephone_code', '')
            patient_instruction.patient_emis_number = patient_emis_number
            patient_instruction.save()
            gp_user = get_object_or_404(GeneralPracticeUser, user_id=request.user.id)
            instruction.saved = True
            instruction.in_progress(context={'gp_user': gp_user})
            next_step = request.POST.get('next_step', '')
            if next_step == 'view_pipeline':
                return redirect('instructions:view_pipeline')
            elif request.POST.get('proceed_option') == '0':
                # Synchronous preparing task case
                prepare_medicalreport_data.delay(instruction_id, notify_mail=False)
                return redirect('medicalreport:select_patient', instruction_id=instruction_id, patient_emis_number=patient_emis_number)
            else:
                # Asynchronous preparing task case
                instruction.status = INSTRUCTION_STATUS_REDACTING
                instruction.saved = False
                instruction.save()
                prepare_medicalreport_data.delay(instruction_id)
                return redirect('instructions:view_pipeline')

    patient_email = patient_registration.email() if not patient_instruction.patient_email else patient_instruction.patient_email
    patient_telephone_mobile = patient_registration.mobile_number() if not patient_instruction.patient_telephone_mobile else patient_instruction.patient_telephone_mobile
    date_format = patient_instruction.patient_dob.strftime("%d/%m/%Y")
    # Initial Patient Form
    patient_form = InstructionPatientForm(
        instance=patient_instruction,
        initial={
            'patient_title': patient_instruction.get_patient_title_display(),
            'patient_first_name': patient_instruction.patient_first_name,
            'patient_last_name': patient_instruction.patient_last_name,
            'patient_postcode': patient_instruction.patient_postcode,
            'patient_address_number': patient_instruction.patient_address_number,
            'patient_email': patient_email,
            'confirm_email': patient_email,
            'patient_telephone_mobile': patient_telephone_mobile,
            'patient_dob': date_format
        }
    )

    consent_type = 'pdf'
    consent_extension = ''
    consent_path = ''
    if instruction.mdx_consent:
        consent_extension = (instruction.mdx_consent.url).split('.')[1]
        consent_path = instruction.mdx_consent.url
    if consent_extension in ['jpeg', 'png', 'gif']:
        consent_type = 'image'
    mdx_consent_form_data = {
        'type': consent_type,
        'path': consent_path
    }
    event_logger.info(
        '{user}:{user_id} ACCESS consent contact view instruction ID {instruction_id}'.format(
            user=request.user, user_id=request.user.id,
            instruction_id=instruction_id
        )
    )

    return render(request, 'instructions/consent_contact.html', {
        'patient_form': patient_form,
        'third_party_form': third_party_form,
        'instruction': instruction,
        'patient_emis_number': patient_emis_number,
        'mdx_consent_form': mdx_consent_form,
        'mdx_consent_form_data': mdx_consent_form_data,
        'reject_types': INSTRUCTION_REJECT_TYPE,
        'patient_full_name': instruction.patient_information.get_full_name()
    })


@login_required(login_url='/accounts/login')
def print_mdx_consent(request, instruction_id, patient_emis_number):
    instruction = get_object_or_404(Instruction, id=instruction_id)
    patient = instruction.patient_information
    gp_practice = instruction.gp_practice

    params = {
        'patient': patient,
        'gp_practice': gp_practice
    }

    return MDXDualConsent.render(params)


def atoi(text: str) -> int:
    return int(text) if text.isdigit() else text


def natural_keys(text: str) -> List[int]:
    if 'Road' in text.split(',')[0]:
        use_text = text.split(',')[0]
    elif 'Road' in text.split(',')[1]:
        use_text = text.split(',')[1]
    elif 'Street' in text.split(',')[1]:
        use_text = text.split(',')[1]
    elif 'Street' in text.split(',')[1]:
        use_text = text.split(',')[1]
    else:
        use_text = text.split(',')[1]

    return [atoi(c) for c in re.split(r'(\d+)', use_text)]


def api_get_address(request: HttpRequest, address: str) -> JsonResponse:
    if not address:
        return JsonResponse({'status': 'error', 'error': 'Address not found.'}, status=404)

    url = 'https://api.getAddress.io/find/' + address + '?api-key=' + settings.GET_ADDRESS_API_KEY + '&sort=True'
    response = requests.get(url)
    json_response = response.json()
    json_response['addresses'].sort(key=natural_keys)
    return JsonResponse(json_response)
