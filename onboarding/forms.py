from django import forms

from accounts import models as accounts_models

from organisations.models import OrganisationGeneralPractice
from common.fields import MyChoiceField
from payment.models import OrganisationFeeRate

import datetime


class OrganisationFeeModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.amount_rate_lvl_1


class SurgeryForm(forms.Form):
    GP_OP_SYS_CHOICES = (
        (
            'EMIS Health', (
                ('EMISWeb', 'EMIS Web'),
                ('LV', 'EMIS LV'),
                ('PCS', 'EMIS PCS')
            )
        ),
        (
            'Microtest Health', (
                ('MT', 'Evolution'),
            )
        ),
        (
            'TPP', (
                ('SystmOne', 'SystmOne'),
            )
        ),
        (
            'Vision Health', (
                ('Vision 3', 'Vision 3'),
                ('VA', 'Vision Anywhere(web)')
            )
        )
    )

    surgery_name = MyChoiceField(choices=[])
    practice_code = MyChoiceField(choices=[])
    postcode = MyChoiceField(choices=[])
    address = MyChoiceField(choices=[], required=False)
    address_line1 = forms.CharField(max_length=255, label='', widget=forms.TextInput())
    address_line2 = forms.CharField(max_length=255, label='', widget=forms.TextInput(), required=False)
    address_line3 = forms.CharField(max_length=255, label='', widget=forms.TextInput(), required=False)
    city = forms.CharField(max_length=20, label='', widget=forms.TextInput())
    county = forms.CharField(max_length=20, label='', widget=forms.TextInput(), required=False)
    contact_num = forms.CharField(max_length=11, label='', widget=forms.TextInput())
    emis_org_code = forms.CharField(max_length=20, label='', widget=forms.TextInput(), required=False)
    operating_system = forms.ChoiceField(choices=GP_OP_SYS_CHOICES, label='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['operating_system'] = 'EW'

    def clean_practice_code(self):
        practice_code = self.cleaned_data.get('practice_code')
        gp_onboarding = OrganisationGeneralPractice.objects.filter(practcode=practice_code).first()
        if gp_onboarding and gp_onboarding.generalpracticeuser_set.first():
            raise forms.ValidationError('A GP Surgery with this practice code already exists. '
                                        'Please contact Medidata for more information, or discuss within your Surgery')
        return practice_code

    def validate_operating_system(self):
        operating_system = self.cleaned_data.get('operating_system')
        if not operating_system == 'EMISWeb':
            self.cleaned_data['accept_policy'] = False
        return operating_system

    def save(self):
        live_timechecked = datetime.datetime.now() if self.data.get('consented') == 'on' else None
        accept_policy = True if self.data.get('accept_policy') == 'on' else False
        gp_organisation = OrganisationGeneralPractice.objects.update_or_create(
            practcode=self.cleaned_data.get('practice_code'),
            defaults={
                'name': self.cleaned_data.get('surgery_name'),
                'accept_policy': accept_policy,
                'live_timechecked': live_timechecked,
                'billing_address_street': self.cleaned_data.get('address_line1'),
                'billing_address_line_2': self.cleaned_data.get('address_line2'),
                'billing_address_line_3': self.cleaned_data.get('address_line3'),
                'billing_address_city': self.cleaned_data.get('city'),
                'billing_address_state': self.cleaned_data.get('county'),
                'billing_address_postalcode': self.cleaned_data.get('postcode'),
                'phone_onboarding_setup': self.cleaned_data.get('contact_num'),
                'operating_system_organisation_code': self.cleaned_data.get('emis_org_code'),
                'gp_operating_system': self.cleaned_data.get('operating_system'),
            }
        )

        return gp_organisation[0]


class SurgeryUpdateForm(forms.Form):
    surgery_name = forms.CharField(max_length=255, label='', disabled=True, required=False)
    surgery_code = forms.CharField(max_length=20, label='', disabled=True, required=False)
    emis_org_code = forms.CharField(max_length=20, label='')
    operating_system = forms.ChoiceField(choices=SurgeryForm.GP_OP_SYS_CHOICES, label='')


class SurgeryEmrSetUpStage2Form(forms.Form):
    surgery_name = forms.CharField(max_length=255, label='', disabled=True)
    surgery_code = forms.CharField(max_length=20, label='', disabled=True)
    address = forms.CharField(max_length=255, label='', disabled=True, widget=forms.Textarea(attrs={'rows': '4'}))
    postcode = forms.CharField(max_length=20, label='', disabled=True)
    surgery_tel_number = forms.CharField(max_length=20, label='', disabled=True)
    surgery_email = forms.CharField(max_length=255, label='', disabled=True)


class UserEmrSetUpStage2Form(forms.Form):
    title = forms.ChoiceField(choices=accounts_models.TITLE_CHOICE, label='')
    first_name = forms.CharField(max_length=255, label='')
    last_name = forms.CharField(max_length=255, label='')
    email = forms.EmailField(max_length=255, label='', widget=forms.EmailInput(attrs={'class': 'form-control input-email'}))
    role = forms.ChoiceField(choices=accounts_models.GeneralPracticeUser.ROLE_CHOICES, label='')
    mobile_code = forms.CharField(max_length=10, label='', widget=forms.HiddenInput(attrs={'placeholder': ''}), required=False)
    mobile_phone = forms.CharField(max_length=255, label='')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if accounts_models.User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address has already been used to register.')
        return email


class SurgeryEmailForm(forms.ModelForm):
    organisation_email = forms.EmailField(max_length=255, label='', widget=forms.EmailInput(attrs={'class': 'form-control input-email'}))
    confirm_email = forms.EmailField(max_length=255, label='')

    class Meta:
        model = OrganisationGeneralPractice
        fields = ('organisation_email',)

    def clean_organisation_email( self ):
        organisation_email = self.cleaned_data.get('organisation_email')
        if accounts_models.User.objects.filter(email=organisation_email).exists():
            raise forms.ValidationError('This email address has already been used to register.')
        else:
            return organisation_email

    def clean_confirm_email(self):
        confirm_email = self.cleaned_data.get('confirm_email')
        organisation_email = self.cleaned_data.get('organisation_email')
        if confirm_email != organisation_email:
            raise forms.ValidationError('The email addresses provided do not match')
        else:
            return confirm_email


class BankDetailsEmrSetUpStage2Form(forms.Form):
    default_rate_band = OrganisationFeeRate.objects.filter(default=True)
    try:
        base_rate_band = default_rate_band.filter(base=True).first()
    except:
        base_rate_band = None
    level_1_payments = base_rate_band.amount_rate_lvl_2 if base_rate_band else 0
    level_2_payments = base_rate_band.amount_rate_lvl_3 if base_rate_band else 0
    level_3_payments = base_rate_band.amount_rate_lvl_4 if base_rate_band else 0

    bank_account_name = forms.CharField(max_length=255, label='', required=False)
    bank_account_number = forms.CharField(max_length=50, label='', required=False)
    bank_account_sort_code = forms.CharField(max_length=50, label='', required=False)
    received_within_3_days = OrganisationFeeModelChoiceField(OrganisationFeeRate.objects.filter(default=True), empty_label=None)
    received_within_4_to_7_days = forms.DecimalField(
        initial=level_1_payments, max_digits=4, label='Received within 4-7 days',
        widget=forms.NumberInput(attrs={'id': 'level_1_payments', 'readonly': True})
    )
    received_within_8_to_11_days = forms.DecimalField(
        initial=level_2_payments, max_digits=4, label='Received within 8-11 days',
        widget=forms.NumberInput(attrs={'id': 'level_2_payments', 'readonly': True})
    )
    received_after_11_days = forms.DecimalField(
        initial=level_3_payments, max_digits=4, label='Received after 11 days',
        widget=forms.NumberInput(attrs={'id': 'level_3_payments', 'readonly': True})
    )
    completed_by = forms.CharField(max_length=255, label='')
    job_title = forms.CharField(max_length=20, label='')
