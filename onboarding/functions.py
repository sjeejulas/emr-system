from django.http import HttpRequest
from accounts.models import User, GeneralPracticeUser
from accounts.models import GENERAL_PRACTICE_USER
from organisations.models import OrganisationGeneralPractice
from payment.models import GpOrganisationFee, OrganisationFeeRate
from .forms import BankDetailsEmrSetUpStage2Form
import random
import string


def create_gp_user(gp_organisation: OrganisationGeneralPractice, user_form: dict=None) -> dict:
    password = User.objects.make_random_password()
    if user_form:
        if not User.objects.filter(email=user_form['email']).exists():
            user = User.objects._create_user(
                email=user_form['email'],
                username=user_form['email'],
                password=password,
                first_name=user_form['first_name'],
                last_name=user_form['last_name'],
                type=GENERAL_PRACTICE_USER,
            )

            general_pratice_user = GeneralPracticeUser.objects.create(
                user=user,
                title=user_form['title'],
                role=user_form['role'],
                organisation=gp_organisation,
                telephone_mobile=user_form['mobile_phone'],
                telephone_code=user_form['mobile_code'],
            )
            return {
                'general_pratice_user': general_pratice_user,
                'password': password
            }
    elif gp_organisation:
        if not User.objects.filter(email=gp_organisation.practicemanager_email).exists():
            if gp_organisation.practicemanagername_c:
                gp_manager_first_name = gp_organisation.practicemanagername_c.split(' ')[0]
                gp_manager_last_name = gp_organisation.practicemanagername_c.split(' ')[1]
                gp_manager_user = User.objects._create_user(
                    email=gp_organisation.practicemanager_email,
                    username=''.join(random.choices(string.ascii_letters, k=10)),
                    password=password,
                    first_name=gp_manager_first_name,
                    last_name=gp_manager_last_name,
                    type=GENERAL_PRACTICE_USER,
                    is_staff=True,
                )

                general_pratice_user = GeneralPracticeUser.objects.create(
                    user=gp_manager_user,
                    role=GeneralPracticeUser.PRACTICE_MANAGER,
                    organisation=gp_organisation,
                )

                return {
                    'general_pratice_user': general_pratice_user,
                    'password': password
                }
            else:
                return {}
    else:
        return {}


def create_gp_payments_fee(bank_details_form: BankDetailsEmrSetUpStage2Form, gp_organisation: OrganisationGeneralPractice) -> OrganisationFeeRate:
    gp_fee_relation = GpOrganisationFee.objects.update_or_create(
        gp_practice=gp_organisation,
        organisation_fee=bank_details_form.cleaned_data['received_within_3_days']
    )

    return bank_details_form.cleaned_data['received_within_3_days']


def update_gp_organisation_bank_details(bank_details_form: BankDetailsEmrSetUpStage2Form, gp_organisation: OrganisationGeneralPractice) -> OrganisationGeneralPractice:
    gp_organisation.payment_bank_holder_name = bank_details_form.cleaned_data['bank_account_name']
    gp_organisation.payment_bank_account_number = bank_details_form.cleaned_data['bank_account_number']
    gp_organisation.payment_bank_sort_code = bank_details_form.cleaned_data['bank_account_sort_code']
    gp_organisation.onboarding_by = bank_details_form.cleaned_data['completed_by']
    gp_organisation.onboarding_job_title = bank_details_form.cleaned_data['job_title']
    gp_organisation.save()

    return gp_organisation