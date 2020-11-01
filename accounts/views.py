import datetime
import dateutil
import pytz

from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.forms import modelformset_factory
from django.contrib.auth import authenticate, login as customlogin
from django.contrib.auth.forms import AuthenticationForm as LoginForm
from django.contrib.auth.models import Permission

from permissions.forms import InstructionPermissionForm, GroupPermissionForm
from permissions.models import InstructionPermission
from common.functions import multi_getattr, verify_password as verify_pass, send_mail
from payment.models import GpOrganisationFee, InstructionVolumeFee, OrganisationFeeRate, WeeklyInvoice
from django_tables2 import RequestConfig
from accounts.forms import AllUserForm, NewGPForm, NewClientForm, NewMediForm,\
        UserProfileForm, UserProfileBaseForm
from instructions.models import Instruction
from instructions.model_choices import INSTRUCTION_STATUS_COMPLETE, INSTRUCTION_STATUS_PAID
from .models import User, UserProfileBase, GeneralPracticeUser, PracticePreferences, ClientUser
from .models import GENERAL_PRACTICE_USER, CLIENT_USER, MEDIDATA_USER
from payment.model_choices import *
from .forms import PracticePreferencesForm, TwoFactorForm, BankDetailsForm, CustomLoginForm, CustomAuthenticationForm
from permissions.functions import access_user_management
from permissions.model_choices import MANAGER_PERMISSIONS, \
                                      OTHER_PERMISSIONS, \
                                      GP_PERMISSIONS
from organisations.models import OrganisationGeneralPractice
from onboarding.views import generate_password
from onboarding.forms import BankDetailsEmrSetUpStage2Form
from axes.models import AccessAttempt
from .tables import AccountTable, PaymentLogTable
from django_tables2 import RequestConfig, Column
from instructions.views import calculate_next_prev
from typing import Union, List, Dict
from instructions.forms import DateRangeSearchForm
from django.conf import settings
DEFAULT_FROM = settings.DEFAULT_FROM

from services.models import SiteAccessControl
from .functions import change_role, remove_user, get_table_data,\
        get_post_new_user_data, get_user_type_form, reset_password,\
        check_ip_from_n3_hscn, get_client_ip


def count_status_invoice_table(query) -> Dict[str, int]:
    complete_total_count = query.filter(status=INSTRUCTION_STATUS_COMPLETE).count()
    paid_total_count = query.filter(status=INSTRUCTION_STATUS_PAID).count()
    all_total_count = query.count()
    filter_number = {
        'All': all_total_count,
        'Completed': complete_total_count,
        'Paid': paid_total_count
    }

    return filter_number


def send_notification_org_email(request, gp_user, status):
    gp_organisation = gp_user.organisation
    gp_name = " ".join([gp_user.user.first_name, gp_user.user.last_name])
    if status == 'is_fee_changed':
        subject = 'New Fee Band Selected'
        message = 'A fee band was selected for your Surgery by "{username}". To review please click here {protocol}://{link}'.format(
            username=gp_name,
            protocol=request.scheme,
            link=request.get_host() + reverse('accounts:view_account')
        )
    elif status == 'update_bank_details':
        subject = 'Changed Bank Account details'
        message = 'Your Surgery bank account details have been changed by "{username}".'.format(
            username=gp_name
        )

    org_email = gp_organisation.organisation_email
    send_mail(
        subject,
        message,
        'MediData',
        [org_email],
        fail_silently=True
    )


@login_required(login_url='/accounts/login')
@access_user_management('instructions.view_account_pages')
def account_view(request: HttpRequest) -> HttpResponse:
    user = request.user

    if request.user.type == 'GP':
        header_title = 'Fee Management'
        gp_user = GeneralPracticeUser.objects.get(pk=user.userprofilebase.generalpracticeuser.pk)
        gp_organisation = gp_user.organisation
        bank_details_info = {
            'payment_bank_holder_name': gp_organisation.payment_bank_holder_name,
            'payment_bank_account_number': gp_organisation.payment_bank_account_number,
            'payment_bank_sort_code': gp_organisation.payment_bank_sort_code,
        }
        bank_details_form = BankDetailsForm(initial=bank_details_info)

        if request.is_ajax():
            if request.POST.get('is_fee_changed'):
                new_organisation_fee_id = request.POST.get('organisation_fee_id')
                GpOrganisationFee.objects.filter(gp_practice=gp_organisation).update(organisation_fee_id=int(new_organisation_fee_id))
                send_notification_org_email(request, gp_user, 'is_fee_changed')
                return JsonResponse({'message': 'Preferences have been saved.'})
            if request.POST.get('update_bank_details'):
                bank_details_form = BankDetailsForm(request.POST, instance=gp_organisation)
                if bank_details_form.is_valid():
                    bank_details_form.save()
                    send_notification_org_email(request, gp_user, 'update_bank_details')
                    return JsonResponse({'message': 'Bank details have been saved.'}, status=200)
                else:
                    return JsonResponse({'message': "Bank details can't saved. please try again."}, status=400)
            gp_preferences_form = PracticePreferencesForm(request.POST, instance=practice_preferences)
            if gp_preferences_form.is_valid():
                gp_preferences_form.save()
                return JsonResponse({'message': 'Bank details have been saved.'})

        organisation = multi_getattr(user, 'userprofilebase.generalpracticeuser.organisation', default=None)
        gp_fee_relation = GpOrganisationFee.objects.filter(gp_practice=organisation).first()
        organisation_fee_data = list()
        organisation_fee = None
        if gp_fee_relation:
            organisation_fee = gp_fee_relation.organisation_fee

        band_fee_rate_data = []
        for fee_structure in OrganisationFeeRate.objects.filter(default=True):
            band_fee_rate_data.append([
                fee_structure.pk,
                float(fee_structure.amount_rate_lvl_1),
                float(fee_structure.amount_rate_lvl_2),
                float(fee_structure.amount_rate_lvl_3),
                float(fee_structure.amount_rate_lvl_4),
            ])

        if organisation_fee:
            organisation_fee_data.append({
                'pk': organisation_fee.pk,
                'days': organisation_fee.max_day_lvl_1,
                'amount': organisation_fee.amount_rate_lvl_1,
                'label': 'Received within %s days'%organisation_fee.max_day_lvl_1
            })
            organisation_fee_data.append({
                'days': organisation_fee.max_day_lvl_2,
                'amount': organisation_fee.amount_rate_lvl_2,
                'label': 'Received within %s-%s days'%(organisation_fee.max_day_lvl_1+1, organisation_fee.max_day_lvl_2)
            })
            organisation_fee_data.append({
                'days': organisation_fee.max_day_lvl_3,
                'amount': organisation_fee.amount_rate_lvl_3,
                'label': 'Received within %s-%s days'%(organisation_fee.max_day_lvl_2+1, organisation_fee.max_day_lvl_3)
            })
            organisation_fee_data.append({
                'days': organisation_fee.max_day_lvl_4,
                'amount': organisation_fee.amount_rate_lvl_4,
                'label': 'Received after %s days'%organisation_fee.max_day_lvl_3
            })

        if request.method == "POST":
            new_organisation_password = generate_password(initial_range=1, body_rage=12, tail_rage=1)
            gp_organisation.set_operating_system_salt_and_encrypted_password(new_organisation_password)
            gp_organisation.save()

            return render(request, 'accounts/accounts_view.html', {
                'header_title': header_title,
                'organisation_fee_data': organisation_fee_data,
                'new_password': new_organisation_password,
                'practice_code': gp_organisation.pk,
                'band_fee_rate_data': band_fee_rate_data
            })

        return render(request, 'accounts/accounts_view.html', {
            'header_title': header_title,
            'organisation_fee_data': organisation_fee_data,
            'band_fee_rate_data': band_fee_rate_data,
            'bank_details_form': bank_details_form
        })

    header_title = 'Fees'
    client_organisation = multi_getattr(request, 'user.userprofilebase.clientuser.organisation', default=None)

    #   Table for block 1
    date_range_form = DateRangeSearchForm()
    cost_column_name = 'Cost £'
    instruction_query_set = Instruction.objects.filter(
        client_user__organisation=client_organisation,
        status__in=[INSTRUCTION_STATUS_COMPLETE, INSTRUCTION_STATUS_PAID]
    )
    filter_number = count_status_invoice_table(instruction_query_set)

    if request.method == 'POST':
        if request.POST.get('from_date', '') and request.POST.get('to_date', ''):
            from_date = dateutil.parser.parse(request.POST.get('from_date', '')).replace(tzinfo=pytz.UTC)
            to_date = dateutil.parser.parse(request.POST.get('to_date', '')).replace(tzinfo=pytz.UTC)
            instruction_query_set = instruction_query_set.filter(completed_signed_off_timestamp__range=(from_date, to_date))
            filter_number = count_status_invoice_table(instruction_query_set)

    page_length = 10
    if 'page_length' in request.GET:
        page_length = int(request.GET.get('page_length'))

    filter_status_btn = int(request.GET.get('status', -1))
    filter_status_search = int(request.GET.get('status_input', -1))
    if filter_status_btn != -1:
        instruction_query_set = instruction_query_set.filter(status=filter_status_btn)
    elif filter_status_search != -1:
        instruction_query_set = instruction_query_set.filter(status=filter_status_search)

    table_block_1 = AccountTable(instruction_query_set, extra_columns=[('cost', Column(empty_values=(), verbose_name=cost_column_name))])
    table_block_1.order_by = '-created'
    table_block_1.paginate(page=request.GET.get('page', 1), per_page=page_length)

    #   Table for block 2
    claim_table = dict()
    under_table = dict()
    sars_table = dict()
    client_fee_query_set = InstructionVolumeFee.objects.filter(client_org=client_organisation)
    for volume_query in client_fee_query_set:
        range_1 = "0-" + str(volume_query.max_volume_band_lowest)
        range_2 = "-".join([str(volume_query.max_volume_band_lowest + 1), str(volume_query.max_volume_band_low)])
        range_3 = "-".join([str(volume_query.max_volume_band_low + 1), str(volume_query.max_volume_band_medium)])
        range_4 = "-".join([str(volume_query.max_volume_band_medium + 1), str(volume_query.max_volume_band_high)])
        range_5 = "-".join([str(volume_query.max_volume_band_high + 1), str(volume_query.max_volume_band_top)])

        if volume_query.fee_rate_type == FEE_CLAIMS_TYPE:
            claim_table[range_1] = round(volume_query.fee_rate_lowest, 2)
            claim_table[range_2] = round(volume_query.fee_rate_low, 2)
            claim_table[range_3] = round(volume_query.fee_rate_medium, 2)
            claim_table[range_4] = round(volume_query.fee_rate_high, 2)
            claim_table[range_5] = round(volume_query.fee_rate_top, 2)
        elif volume_query.fee_rate_type == FEE_UNDERWRITE_TYPE:
            under_table[range_1] = round(volume_query.fee_rate_lowest, 2)
            under_table[range_2] = round(volume_query.fee_rate_low, 2)
            under_table[range_3] = round(volume_query.fee_rate_medium, 2)
            under_table[range_4] = round(volume_query.fee_rate_high, 2)
            under_table[range_5] = round(volume_query.fee_rate_top, 2)
        elif volume_query.fee_rate_type == FEE_SARS_TYPE:
            sars_table[range_1] = round(volume_query.fee_rate_lowest, 2)
            sars_table[range_2] = round(volume_query.fee_rate_low, 2)
            sars_table[range_3] = round(volume_query.fee_rate_medium, 2)
            sars_table[range_4] = round(volume_query.fee_rate_high, 2)
            sars_table[range_5] = round(volume_query.fee_rate_top, 2)

    #   Table for block 3
    gp_rate_query_set = OrganisationFeeRate.objects.filter(default=True)
    table_block_3 = dict()
    value_amount_1 = list()
    value_amount_2 = list()
    value_amount_3 = list()
    value_amount_4 = list()

    key_1 = "0-3"
    key_2 = "4-7"
    key_3 = "8-11"
    key_4 = "11+"

    for record in gp_rate_query_set:
        value_amount_1.append(round(record.amount_rate_lvl_1, 2))
        value_amount_2.append(round(record.amount_rate_lvl_2, 2))
        value_amount_3.append(round(record.amount_rate_lvl_3, 2))
        value_amount_4.append(round(record.amount_rate_lvl_4, 2))

    table_block_3[key_1] = value_amount_1
    table_block_3[key_2] = value_amount_2
    table_block_3[key_3] = value_amount_3
    table_block_3[key_4] = value_amount_4

    #   Table for block 4
    weekly_query = WeeklyInvoice.objects.filter(client_org=client_organisation)
    table_block_4 = PaymentLogTable(weekly_query)
    table_block_4.order_by = '-start_date'
    table_block_4.paginate(page=request.GET.get('page_weekly', 1), per_page=5)

    return render(request, 'accounts/accounts_view_client.html', {
        'header_title': header_title,
        'filter_number': filter_number,
        'page_length': page_length,
        'invoicing_table': table_block_1,
        'filter_status': filter_status_btn,
        'date_range_form': date_range_form,
        'claim_table': claim_table,
        'under_table': under_table,
        'sars_table': sars_table,
        'GPRate_table': table_block_3,
        'weekly_table': table_block_4
    })        


@login_required(login_url='/accounts/login')
def manage_user(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        action_type = request.POST.get("action_type")
        if action_type == "Remove":
            remove_user(request)

        elif action_type == "Change":
            change_role(request)

        elif action_type == "Reset Password":
            reset_password(request)

        return JsonResponse({"success": "true"})


@login_required(login_url='/accounts/login')
@access_user_management('organisations.view_user_management')
def view_users(request: HttpRequest) -> HttpResponse:
    header_title = "User Management"
    profiles = UserProfileBase.all_objects.all()
    user = request.user
    user = User.objects.get(username=user.username)
    user_profile = UserProfileBase.objects.filter(user_id=user.pk).first()

    if 'status' in request.GET:
        filter_type = request.GET.get('type', 'active')
        filter_status = request.GET.get('status', -1)
        filter_user_type = request.GET.get('user_type', None)
        if filter_status == 'undefined':
            filter_status = -1
        else:
            filter_status = int(filter_status)
        if filter_type == 'undefined':
            filter_type = 'active'
    else:
        filter_type = request.COOKIES.get('type')
        filter_status = int(request.COOKIES.get('status', -1))
        filter_user_type = request.COOKIES.get('user_type', None)

    if filter_type == '':
        filter_type = "active"
    user_types = [MEDIDATA_USER, CLIENT_USER, GENERAL_PRACTICE_USER]
    query_set = user.get_query_set_within_organisation().filter(type__in=user_types)

    if filter_type == 'active':
        query_set = query_set.filter(is_active=True)
    elif filter_type == 'deactivated':
        query_set = query_set.filter(is_active=False)

    filter_query = query_set
    if filter_status != -1:
        if (filter_user_type and filter_user_type == GENERAL_PRACTICE_USER) or hasattr(user.userprofilebase, 'generalpracticeuser'):
            filter_query = query_set.filter(userprofilebase__generalpracticeuser__role=filter_status)
        elif (filter_user_type and filter_user_type == CLIENT_USER) or hasattr(user.userprofilebase, 'clientuser'):
            filter_query = query_set.filter(userprofilebase__clientuser__role=filter_status)
        else:
            filter_query = query_set.filter(type=MEDIDATA_USER)

    table_data = get_table_data(user, query_set, filter_query)
    RequestConfig(request, paginate={'per_page': 5}).configure(table_data['table'])
    table_data['table'].order_by = request.GET.get('sort', '-created')
    permission_formset = []

    if user_profile and hasattr(user_profile, 'generalpracticeuser'):
        organisation = user_profile.generalpracticeuser.organisation
        permissions = InstructionPermission.objects.filter(organisation=organisation)
        permission_set = modelformset_factory(InstructionPermission, form=InstructionPermissionForm, extra=(3-permissions.count()))
        initial_data = set_initial_data_permission(permissions, organisation.pk)
        permission_formset = permission_set(queryset=permissions, initial=initial_data)
    elif user_profile and hasattr(user_profile, 'medidatauser'):
        permissions = InstructionPermission.objects.filter(global_permission=True)
        permission_set = modelformset_factory(InstructionPermission, form=InstructionPermissionForm, extra=(3-permissions.count()))
        initial_data = set_initial_data_permission(permissions, None)
        permission_formset = permission_set(queryset=permissions, initial=initial_data)

    #Get names of fixed permissions...
    fixed_permissions_list = MANAGER_PERMISSIONS + \
                             OTHER_PERMISSIONS + \
                             GP_PERMISSIONS
    fixed_permissions = Permission.objects.filter(
            Q(codename__in = fixed_permissions_list))
    fixed_perm_names = [perm.name for perm in fixed_permissions] + ['view account page']

    show_pop_up = ''
    if request.GET.get('show'):
        show_pop_up = 'show'

    if user.type == 'GP':
        gp_user = GeneralPracticeUser.objects.get(
            pk = user.userprofilebase.generalpracticeuser.pk)
        gp_organisation = gp_user.organisation

        try:
            practice_preferences = PracticePreferences.objects.filter(
                gp_organisation__practcode = gp_organisation.practcode).first()
        except PracticePreferences.DoesNotExist:
            practice_preferences = PracticePreferences()
            practice_preferences.gp_organisation = gp_organisation
            practice_preferences.notification = 'NEW'
            practice_preferences.save()

        gp_preferences_form = PracticePreferencesForm(
            instance = practice_preferences)
        response = render(request, 'user_management/user_management.html', {
            'user': user,
            'header_title': header_title,
            'table': table_data['table'],
            'overall_users_number': table_data['overall_users_number'],
            'permission_formset': permission_formset,
            'gp_preferences_form': gp_preferences_form,
            'user_type': table_data['user_type'],
            'show_pop_up': show_pop_up,
            'fixed_permission_names': fixed_perm_names
        })
    else:
        response = render(request, 'user_management/user_management.html', {
            'user': user,
            'header_title': header_title,
            'table': table_data['table'],
            'overall_users_number': table_data['overall_users_number'],
            'permission_formset': permission_formset,
            'user_type': table_data['user_type'],
            'show_pop_up': show_pop_up,
            'fixed_permission_names': fixed_perm_names
        })

    return response


def set_initial_data_permission(permissions: InstructionPermission, organisation_id: Union[str, None]) -> List[Dict[str, str]]:
    initial_data = []
    for key, value in GeneralPracticeUser.ROLE_CHOICES:
        if key is '': continue
        if key not in permissions.values('role'):
            initial_data.append({'organisation': organisation_id, 'role': key})
    return initial_data


@login_required(login_url='/accounts/login')
@access_user_management('permissions.change_instructionpermission')
def update_permission(request: HttpRequest) -> HttpResponse:
    request.META['HTTP_REFERER'] = ''
    if request.method == 'POST':
        user = request.user
        user = User.objects.get(pk=user.id)
        user_profile = UserProfileBase.objects.filter(user_id=user.pk).first()
        permission_set = modelformset_factory(InstructionPermission, form=InstructionPermissionForm, extra=0)
        permission_formset = permission_set(request.POST, form_kwargs={'empty_permitted': False})
        if permission_formset.is_valid():
            for form in permission_formset:
                if user.type == MEDIDATA_USER:
                    set_all_permissions(request, form)
                else:
                    set_permission(request, form)
    response = redirect('accounts:view_users')
    response['Location'] += "?show=True"
    return response


@login_required(login_url='/accounts/login')
def update_notification(request: HttpRequest) -> HttpResponse:
    user = request.user
    gp_user = GeneralPracticeUser.objects.get(
        pk = user.userprofilebase.generalpracticeuser.pk)
    gp_organisation = gp_user.organisation
    practice_preferences = PracticePreferences.objects \
        .filter(
            gp_organisation__practcode = gp_organisation.practcode) \
        .first()

    if request.is_ajax():
        gp_preferences_form = PracticePreferencesForm(
            request.POST,instance = practice_preferences)

        if gp_preferences_form.is_valid():
            gp_preferences_form.save()

    response = redirect('accounts:view_users')
    return response


def set_all_permissions(request, form):
    permission = form.save(commit=False)
    data = form.cleaned_data
    for organisation in OrganisationGeneralPractice.objects.filter(accept_policy=True, live=True):
        gp_permission, create = InstructionPermission.objects.get_or_create(organisation=organisation, role=permission.role)
        data['name'] = '%s : %s' % (permission.get_role_display(), organisation.__str__())
        if gp_permission.group:
            group_form = GroupPermissionForm(data, instance=gp_permission.group)
        else:
            group_form = GroupPermissionForm(data)

        if group_form.is_valid():
            group = group_form.save()
            gp_permission.group = group
            gp_permission.save()
            gp_permission.allocate_permission_to_gp()

    data['name'] = '%s : MediData' % permission.get_role_display()
    if permission.group:
        group_form = GroupPermissionForm(data, instance=gp_permission.group)
    else:
        group_form = GroupPermissionForm(data)

    if group_form.is_valid():
        group = group_form.save()
        permission.group = group
        permission.global_permission = True
        permission.save()


def set_permission(request, form):
    permission = form.save(commit=False)
    data = form.cleaned_data
    data['name'] = permission.__str__()
    if permission.group:
        group_form = GroupPermissionForm(data, instance=permission.group)
    else:
        group_form = GroupPermissionForm(data)
    group = group_form.save()
    permission.group = group
    permission.save()
    permission.allocate_permission_to_gp()


@login_required(login_url='/accounts/login')
@access_user_management('organisations.add_user_management')
def create_user(request: HttpRequest) -> HttpResponse:
    header_title = "Add New User"

    cur_user = request.user
    cur_user = User.objects.get(username=cur_user.username)

    if request.method == 'POST':
        user_role = request.POST.get("user_role")
        new_user_data = get_post_new_user_data(cur_user, request, user_role)
        organisation = new_user_data['organisation']
        newuser_form = new_user_data['newuser_form']
        user_type = new_user_data['user_type']

        if not user_role:
            messages.warning(request, 'Please input all the fields properly.')
        elif newuser_form.is_valid():
            user = User.objects.filter(
                Q(username=newuser_form.cleaned_data['username']) |
                Q(email=newuser_form.cleaned_data['email'])
            )
            if not user.exists():
                user = User.objects.create(
                    first_name=newuser_form.cleaned_data['first_name'],
                    last_name=newuser_form.cleaned_data['last_name'],
                    email=newuser_form.cleaned_data['email'],
                    username=newuser_form.cleaned_data['email']
                )
                user.type = user_type
                user.is_staff = new_user_data['is_staff']
                user.set_password(newuser_form.cleaned_data['password'])
                user.save()

                newuser = newuser_form.save(commit=False)
                newuser.organisation = organisation
                newuser.role = user_role
                newuser.user = user
                newuser.save()
                reset_password_form = PasswordResetForm(data={'email': user.email})
                if newuser_form.cleaned_data['send_email'] and reset_password_form.is_valid():
                    reset_password_form.save(
                        request=request,
                        from_email=DEFAULT_FROM,
                        subject_template_name='registration/password_reset_subject_new.txt',
                        email_template_name='registration/password_reset_email_new.html')
                messages.success(request, 'New User Account created successfully.')
                return redirect("accounts:view_users")
            else:
                messages.warning(request, 'User Account Existing In Database')
        else:
            messages.warning(request, 'Please input all the fields properly.')

    user_type_form = get_user_type_form(cur_user)
    newuser_form = user_type_form['newuser_form']
    user_type = user_type_form['user_type']

    response = render(request, 'user_management/new_user.html', {
        'header_title': header_title,
        'newuser_form': newuser_form,
        'user_type': user_type
    })

    return response


@login_required(login_url='/accounts/login')
@access_user_management('organisations.change_user_management')
def medi_change_user(request, email):
    user = User.objects.filter(email=email).first()
    initial_data = {
        'user_type': user.type,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'username': user.username,
        'password': user.password
    }
    if hasattr(user, 'userprofilebase'):
        user_profile = user.userprofilebase
        if hasattr(user_profile, 'generalpracticeuser'):
            gp = user.userprofilebase.generalpracticeuser
            initial_data['gp_organisation'] = gp.organisation
            initial_data['payment_bank_holder_name'] = gp.payment_bank_holder_name
            initial_data['payment_bank_sort_code'] = gp.payment_bank_sort_code
            initial_data['payment_bank_account_number'] = gp.payment_bank_account_number
            initial_data['role'] = gp.role
        elif hasattr(user_profile, 'clientuser'):
            client = user.userprofilebase.clientuser
            initial_data['client_organisation'] = client.organisation
            initial_data['role'] = client.role
        elif hasattr(user_profile, 'medidatauser'):
            organisation = user.userprofilebase.medidatauser.organisation
            initial_data['medi_organisation'] = organisation

    if request.method == 'POST':
        newuser_form = AllUserForm(request.POST)
        if newuser_form.is_valid():
            data = newuser_form.cleaned_data
            user.first_name = data['first_name']
            user.last_name = data['last_name']
            user.email = data['email']
            user.save()
            if data['user_type'] == GENERAL_PRACTICE_USER:
                gp = user.userprofilebase.generalpracticeuser
                user_form = NewGPForm(request.POST, instance=gp)
                organisation = data['gp_organisation']
            elif data['user_type'] == CLIENT_USER:
                client = user.userprofilebase.clientuser
                user_form = NewClientForm(request.POST, instance=client)
                organisation = data['client_organisation']
            else:
                medi = user.userprofilebase.medidatauser
                user_form = NewMediForm(request.POST, instance=medi)
                organisation = data['medi_organisation']
            if user_form.is_valid():
                newuser = user_form.save(commit=False)
                newuser.organisation = organisation
                if user.type != MEDIDATA_USER:
                    newuser.role = data.get('role')
                newuser.save()
                messages.success(request, 'User updated successfully.')
                return redirect("accounts:view_users")
            else:
                messages.warning(request, user_form.errors)

    newuser_form = AllUserForm(initial=initial_data)
    response = render(request, 'user_management/medi_update_user.html', {
        'newuser_form': newuser_form,
        'user': user,
    })
    return response


@login_required(login_url='/accounts/login')
@access_user_management('organisations.add_user_management')
def medi_create_user(request: HttpRequest) -> HttpResponse:
    newuser_form = AllUserForm()
    if request.method == 'POST':
        newuser_form = AllUserForm(request.POST)
        if newuser_form.is_valid():
            data = newuser_form.cleaned_data
            user = User.objects.filter(
                Q(username=data['username']) |
                Q(email=data['email'])
            )
            if not user.exists():
                user = User.objects.create(
                    first_name=newuser_form.cleaned_data['first_name'],
                    last_name=newuser_form.cleaned_data['last_name'],
                    username=newuser_form.cleaned_data['username'],
                    email=newuser_form.cleaned_data['email'],
                    type=data['user_type']
                )
                user.set_password(newuser_form.cleaned_data['password'])
                user.save()
                if data['user_type'] == GENERAL_PRACTICE_USER:
                    user_form = NewGPForm(request.POST)
                    organisation = data['gp_organisation']
                elif data['user_type'] == CLIENT_USER:
                    user_form = NewClientForm(request.POST)
                    organisation = data['client_organisation']
                else:
                    user_form = NewMediForm(request.POST)
                    organisation = data['medi_organisation']
                if user_form.is_valid():
                    newuser = user_form.save(commit=False)
                    newuser.organisation = organisation
                    if user.type != MEDIDATA_USER:
                        newuser.role = data.get('role')
                    newuser.user = user
                    newuser.save()
                    reset_password_form = PasswordResetForm(data={'email': user.email})
                    if newuser_form.cleaned_data['send_email'] and reset_password_form.is_valid():
                        reset_password_form.save(
                            request=request,
                            from_email=DEFAULT_FROM,
                            subject_template_name='registration/password_reset_subject_new.txt',
                            email_template_name='registration/password_reset_email_new.html')
                    messages.success(request, 'New User Account created successfully.')
                    return redirect("accounts:view_users")
                else:
                    messages.warning(request, user_form.errors)
            else:
                messages.warning(request, 'User Account Existing In Database')
    response = render(request, 'user_management/medi_create_user.html', {
        'newuser_form': newuser_form,
    })
    return response


def verify_password(request: HttpRequest) -> JsonResponse:
    password = request.POST.get('password')
    first_name = request.POST.get('first_name')
    surname = request.POST.get('surname')
    email = request.POST.get('email')
    results = verify_pass(password, first_name, surname, email)
    return JsonResponse({'results': results})


def check_email(request: HttpRequest) -> JsonResponse:
    email = request.POST.get('email')
    exists = User.objects.filter(email=email).exists()
    return JsonResponse({'exists': exists})


def login(request: HttpRequest) -> HttpResponse:
    site = request.get_host()
    access_control = SiteAccessControl.objects.filter(site_host=site).first()
    if access_control:
        if access_control.active_host or not settings.SITE_CONTROL:
            if request.method == 'POST':
                #Set client ip for axes
                client_ip_attribute = 'axes_client_ip'
                client_ip = get_client_ip(request)
                setattr(request, client_ip_attribute, client_ip)

                form = CustomLoginForm(request, request.POST)
                if form.is_valid():
                    username = request.POST['username']
                    password = request.POST['password']
                    user = authenticate(request, username=username, password=password)
                    if user is not None and settings.TWO_FACTOR_ENABLED\
                            and settings.SITE_CONTROL\
                            and not check_ip_from_n3_hscn(request)\
                            and not user.is_superuser:
                        request.session['post_data'] = request.POST
                        return redirect(reverse('accounts:two_factor'))
                    elif user is not None:
                        customlogin(request, user)
                        return redirect(reverse('instructions:view_pipeline'))
            else:
                form = CustomAuthenticationForm()
            if check_lock_out(request):
                return redirect(reverse('accounts:locked_out'))
            return render(request, 'registration/login.html', {
                'form': form,
                'mdx_url': settings.MDX_URL
            })

    return HttpResponse('Site is not active !')


def two_factor(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        form = TwoFactorForm(request.POST)
        if form.is_valid():
            customlogin(request, user)
            return redirect(reverse('instructions:view_pipeline'))
    else:
        post_data = request.session.get('post_data')
        if not post_data:
            return redirect(reverse('accounts:login'))
        username = post_data['username']
        password = post_data['password']
        user = authenticate(request, username=username, password=password)
        form = TwoFactorForm(initial={
            'user': user,
            'username': username,
            'password': password
        })
    return render(request, 'registration/two_factor.html', {
        'form': form,
        'user': user
    })


@login_required(login_url='/accounts/login')
def view_profile(request: HttpRequest) -> HttpResponse:
    header_title = 'Profile'
    user = User.objects.get(pk=request.user.pk)
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=user)
        profile_form = UserProfileBaseForm(request.POST, instance=user.userprofilebase)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
        messages.success(request, 'Profile updated successfully.')
    else:
        user_form = UserProfileForm(instance=user)
        profile_form = UserProfileBaseForm(instance=user.userprofilebase)
    return render(request, 'accounts/accounts_profile.html', {
        'header_title': header_title,
        'user_form': user_form,
        'profile_form': profile_form
    })


def check_lock_out(request: HttpRequest) -> bool:
    ip = get_client_ip(request)
    for access in AccessAttempt.objects.filter(ip_address=ip):
        if access.failures >= settings.AXES_FAILURE_LIMIT:
            return True
    return False


def locked_out(request: HttpRequest) -> HttpResponse:
    return render(request, 'registration/locked_out.html')
