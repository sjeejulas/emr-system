from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.template import loader
from django.conf import settings
from django.forms import formset_factory
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .functions import *
from .forms import *
from accounts.forms import PMForm
from services.emisapiservices.services import GetEmisStatusCode
from organisations.models import OrganisationGeneralPractice
from permissions.functions import generate_gp_permission
from payment.models import GpOrganisationFee, OrganisationFeeRate
from common.functions import get_url_page, send_mail
import random
import string
import logging
from medi.settings.common import PREFIX_EMIS_USER


event_logger = logging.getLogger('medidata.event')


def generate_password(initial_range: int, body_rage: int, tail_rage: int) -> str:
    initial_password = random.choices(string.ascii_uppercase, k=initial_range)
    body_password = random.choices(string.ascii_letters + string.digits, k=body_rage)
    tail_password = random.choices(string.digits, k=tail_rage)
    password = ''.join(initial_password + body_password + tail_password)
    return password


@login_required(login_url='/accounts/login')
def emis_setup_success(request: HttpRequest) -> HttpResponse:
    messages.success(request, 'Create User Successful!')
    login_link = request.build_absolute_uri(reverse('accounts:login',))
    welcome_message1 = 'Onboarding Successful!'
    welcome_message2 = 'Welcome to the eMR System'
    return render(request, 'onboarding/emr_message.html', {
        'welcome_message1': welcome_message1,
        'welcome_message2': welcome_message2,
        'login_link': login_link,
    })


def ajax_emis_polling(request: HttpRequest, practice_code: str) -> JsonResponse:
    data = {
        'status': 401,
        'practice_code': ''
    }
    gp_organisation = OrganisationGeneralPractice.objects.filter(practcode=practice_code).first()
    if gp_organisation:
        status = GetEmisStatusCode(gp_organisation=gp_organisation).call()
        if status >= 200 and status < 400:
            if gp_organisation.gp_operating_system == 'EMISWeb' and gp_organisation.accept_policy:
                gp_organisation.live =True
                gp_organisation.save()
            generate_gp_permission(gp_organisation)
        data['status'] = status
        data['practice_code'] = gp_organisation.practcode

    return JsonResponse(data, safe=False)


def step1(request: HttpRequest) -> HttpResponse:
    surgery_form = SurgeryForm()
    surgery_email_form = SurgeryEmailForm()
    if request.method == "POST":
        surgery_form = SurgeryForm(request.POST)
        if surgery_form.is_valid():
            gp_organisation = surgery_form.save()
            if not surgery_form.cleaned_data.get('operating_system') == 'EMISWeb':
                message_1 = 'Thank you for completing part one of the eMR registration process. It’s great to have you on board.'
                message_2 = 'We will be in touch with you shortly to complete the set up process so that you can process SARs in seconds.'
                message_3 = 'We look forward to working with you in the very near future. eMR Support Team'
                return render(request, 'onboarding/emr_message.html', context={
                    'message_1': message_1,
                    'message_2': message_2,
                    'message_3': message_3
                })
            if gp_organisation.practcode[:4] == 'TEST':
                gp_organisation.operating_system_username = 'michaeljtbrooks'
                gp_organisation.operating_system_salt_and_encrypted_password = 'Medidata2019'
            else:
                password = generate_password(initial_range=1, body_rage=12, tail_rage=1)
                gp_organisation.operating_system_salt_and_encrypted_password = password
                gp_organisation.operating_system_username = PREFIX_EMIS_USER + gp_organisation.operating_system_organisation_code
            gp_organisation.save()

            if not OrganisationFeeRate.objects.filter(default=True).exists():
                OrganisationFeeRate.objects.create(
                    name='Default Band',
                    amount_rate_lvl_1=60,
                    amount_rate_lvl_2=57,
                    amount_rate_lvl_3=51,
                    amount_rate_lvl_4=45,
                    default=True
                )

            # setup default fee policy
            GpOrganisationFee.objects.create(
                gp_practice=gp_organisation,
                organisation_fee=OrganisationFeeRate.objects.filter(default=True).first()
            )

            surgery_email_form = SurgeryEmailForm(request.POST, instance=gp_organisation)

            if surgery_email_form.is_valid():
                surgery_email = surgery_email_form.save()
                if surgery_email.organisation_email:
                    html_message = loader.render_to_string('onboarding/surgery_email.html')
                    send_mail(
                        'eMR successful set up',
                        '',
                        settings.DEFAULT_FROM,
                        [surgery_email.organisation_email],
                        fail_silently=True,
                        html_message=html_message,
                    )

                return redirect('onboarding:step2', practice_code=gp_organisation.practcode)

    return render(request, 'onboarding/step1.html', {
        'surgery_form': surgery_form,
        'surgery_email_form': surgery_email_form,
    })


def step2(request: HttpRequest, practice_code: str) -> HttpResponse:
    gp_organisation = get_object_or_404(OrganisationGeneralPractice, pk=practice_code)
    pm_form = PMForm()
    UserEmrSetUpStage2Formset = formset_factory(UserEmrSetUpStage2Form, validate_min=True, extra=4)
    user_formset = UserEmrSetUpStage2Formset()
    if request.method == 'POST':
        home_page_link = request.scheme + '://' + get_url_page('home', request=request)
        pm_form = PMForm(request.POST)
        user_formset = UserEmrSetUpStage2Formset(request.POST)
        if pm_form.is_valid() and user_formset.is_valid():
            created_user_list = []
            pm_form.save__with_gp(gp_organisation=gp_organisation)

            for user in user_formset:
                if user.is_valid() and user.cleaned_data:
                    created_user_dict = create_gp_user(gp_organisation, user_form=user.cleaned_data)
                    if created_user_dict:
                        created_user_list.append(created_user_dict)

            for user in created_user_list:
                html_message = loader.render_to_string('onboarding/emr_setup_2_email.html', {
                    'user_email': user['general_pratice_user'].user.email,
                    'user_password': user['password'],
                    'home_page_link': home_page_link
                })
                send_mail(
                    'eMR New User Account information',
                    '',
                    settings.DEFAULT_FROM,
                    [user['general_pratice_user'].user.email],
                    fail_silently=True,
                    html_message=html_message,
                )

            new_pm_user = authenticate(
                request,
                email=pm_form.cleaned_data['email1'],
                password=pm_form.cleaned_data['password1'],
            )
            login(request, new_pm_user)
            return redirect('onboarding:step3', practice_code=gp_organisation.practcode)

    return render(request, 'onboarding/step2.html', {
        'pm_form': pm_form,
        'user_formset': user_formset,
    })


@login_required(login_url='/accounts/login')
def step3(request: HttpRequest, practice_code: str) -> HttpResponse:
    header_title = "Sign up: eMR with EMISweb - please make sure to only minimise this browser tab, do not close this screen "
    gp_organisation = OrganisationGeneralPractice.objects.filter(practcode=practice_code).first()
    reload_status = 0
    if not request.user.pk or request.user.get_my_organisation() != gp_organisation:
        return redirect('accounts:login')

    if request.method == "POST":
        surgery_update_form = SurgeryUpdateForm(request.POST)
        if surgery_update_form.is_valid():
            gp_organisation.operating_system_organisation_code = surgery_update_form.cleaned_data['emis_org_code']
            gp_organisation.gp_operating_system = surgery_update_form.cleaned_data['operating_system']
            if gp_organisation.practcode[:4] != 'TEST':
                gp_organisation.operating_system_username = PREFIX_EMIS_USER + surgery_update_form.cleaned_data['emis_org_code']
            gp_organisation.save()

            event_logger.info('Onboarding: {gp_name}, EDITED surgery information completed'.format(gp_name=gp_organisation.name))
            #   If User selected the another os. Will redirect to thank you Page.
            if not gp_organisation.gp_operating_system == 'EMISWeb':
                message_1 = 'Thank you for completing part one of the eMR registration process. It’s great to have you on board.'
                message_2 = 'We will be in touch with you shortly to complete the set up process so that you can process SARs in seconds.'
                message_3 = 'We look forward to working with you in the very near future. eMR Support Team'
                return render(request, 'onboarding/emr_message.html', context={
                    'message_1': message_1,
                    'message_2': message_2,
                    'message_3': message_3
                })
            reload_status = 1

    surgery_update_form = SurgeryUpdateForm(initial={
        'surgery_name': gp_organisation.name,
        'surgery_code': gp_organisation.practcode,
        'emis_org_code': gp_organisation.operating_system_organisation_code,
        'operating_system': gp_organisation.gp_operating_system
    })

    request.session.set_expiry(settings.DEFAULT_SESSION_COOKIE_AGE)
    practice_username = PREFIX_EMIS_USER + gp_organisation.operating_system_organisation_code

    return render(request, 'onboarding/step3.html', {
        'header_title': header_title,
        'organisation_code': gp_organisation.operating_system_organisation_code,
        'practice_code': gp_organisation.practcode,
        'practice_username': practice_username,
        'practice_password': gp_organisation.operating_system_salt_and_encrypted_password,
        'surgery_update_form': surgery_update_form,
        'reload_status': reload_status
    })
