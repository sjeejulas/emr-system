from django import forms
from django.conf import settings
from django.utils.timezone import now
from django.contrib.auth.forms import AuthenticationForm
from common.functions import verify_password
from .models import GeneralPracticeUser, ClientUser, TITLE_CHOICE, User,\
        MEDIDATA_USER, CLIENT_USER, GENERAL_PRACTICE_USER, PATIENT_USER,\
        MedidataUser, NOTIFICATIONS, PracticePreferences, UserProfileBase
from instructions.models import InstructionPatient
from organisations.models import OrganisationGeneralPractice, OrganisationClient, OrganisationMedidata
from report.mobile import AuthMobile
from common.fields import MyChoiceField
from services.models import SiteAccessControl
import json
DATE_INPUT_FORMATS = settings.DATE_INPUT_FORMATS


class InstructionPatientForm(forms.ModelForm):
    confirm_email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': '', 'id' : 'confirm_email'}), required=False)
    patient_dob = forms.DateField(show_hidden_initial=True, input_formats=DATE_INPUT_FORMATS)
    patient_dob_day = forms.ChoiceField(choices=((str(x), x) for x in range(1, 32)), label='Day')
    patient_dob_month = forms.ChoiceField(choices=((str(x), x) for x in range(1, 13)), label='Month')
    patient_dob_year = forms.ChoiceField(choices=((str(x), x) for x in range(1900, now().year)), label='Year')
    patient_postcode = MyChoiceField(required=True, label='Address postcode')
    patient_address_number = MyChoiceField(required=False, label='Address name number')
    patient_address_line1 = forms.CharField(max_length=255, required=True)
    patient_address_line2 = forms.CharField(max_length=255, required=False)
    patient_address_line3 = forms.CharField(max_length=255, required=False)
    patient_city = forms.CharField(max_length=255, required=True)
    patient_county = forms.CharField(max_length=255, required=False, label="Patient county")

    class Meta:
        model = InstructionPatient
        exclude = ('instruction', 'patient_user')
        widgets = {
            'patient_postcode': forms.TextInput(attrs={'placeholder': '', }),
            'patient_address_number': forms.TextInput(attrs={'placeholder': '', }),
            'patient_telephone_code': forms.HiddenInput(attrs={'placeholder': ''}),
            'patient_alternate_code': forms.HiddenInput(attrs={'placeholder': ''})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial_data = kwargs.get('initial')
        if initial_data:
            edit_patient = initial_data.get('edit_patient')
            if not edit_patient:
                post_code = initial_data.get('patient_postcode')
                address_number = initial_data.get('patient_address_number')
                if post_code:
                    self.fields['patient_postcode'] = forms.CharField(max_length=255, label='Address postcode')

                if address_number:
                    self.fields['patient_address_number'] = forms.CharField(max_length=255, label='Address name number')

                self.fields['patient_title'] = forms.CharField(max_length=255, label='Title*')

    def clean_patient_email(self):
        email = self.cleaned_data.get('patient_email')
        if User.objects.filter(email= email).exclude(type=PATIENT_USER).exists():
            raise forms.ValidationError('{email} already used by user that is not Patient'.format(email=email))
        return email

    @classmethod
    def str_to_date(cls, day, month, year):
        return '/'.join([day, month, year])

    @classmethod
    def change_request_date(cls, request):
        request['patient_dob'] = InstructionPatientForm.str_to_date(request.get('patient_dob_day'),
                                                 request.get('patient_dob_month'),
                                                 request.get('patient_dob_year')
                                                 )
        return request


class GPForm(forms.Form):
    gp_title = forms.ChoiceField(choices=TITLE_CHOICE, required=False)
    initial = forms.CharField(max_length=255, required=False, label='Initials', widget=forms.TextInput(attrs={'placeholder': ''}))
    gp_last_name = forms.CharField(max_length=255, required=False, label='Last Name', widget=forms.TextInput(attrs={'id': 'gp_last_name', 'name': 'gp_last_name', 'placeholder': '',}))

    class Meta:
        model = GeneralPracticeUser
        fields = ('gp_title', 'initial', 'gp_last_name')

        labels = {
            'gp_title': 'Title'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial_data = kwargs.get('initial')
        if initial_data:
            self.fields['gp_title'] = forms.CharField(max_length=255, label='Title')


class PMForm(forms.ModelForm):
    title = forms.ChoiceField(choices=TITLE_CHOICE, required=True)
    first_name = forms.CharField(max_length=255, required=True, label='')
    surname = forms.CharField(max_length=255, required=True, label='')
    email1 = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': ''}), label='', required=True)
    email2 = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': ''}), label='', required=True)
    password1 = forms.CharField(required=True, widget=forms.PasswordInput())
    password2 = forms.CharField(required=True, widget=forms.PasswordInput())
    telephone_mobile = forms.CharField(required=True)
    telephone_code = forms.CharField(required=True, widget=forms.HiddenInput())

    class Meta:
        model = GeneralPracticeUser
        fields = (
            'first_name', 'surname', 'email1',
            'email2', 'password1', 'password2',
            'telephone_mobile', 'telephone_code'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # initial_data = kwargs.get('initial')

    def clean_email1(self):
        email = self.cleaned_data.get('email1')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address has already been used to register.')
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        first_name = self.cleaned_data.get('first_name')
        surname = self.cleaned_data.get('surname')
        email = self.cleaned_data.get('email1')
        password_auth = verify_password(password, first_name, surname, email)
        if not password_auth.get('verified'):
            raise forms.ValidationError(password_auth.get('warning'))
        return password

    def clean_email2(self):
        email = self.cleaned_data.get('email2')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address has already been used to register.')
        return email

    def save__with_gp(self, gp_organisation=None):
        gp_manager_user = User.objects._create_user(
            email=self.cleaned_data.get('email1'),
            username=self.cleaned_data.get('email1'),
            password=self.cleaned_data.get('password1'),
            first_name=self.cleaned_data.get('first_name'),
            last_name=self.cleaned_data.get('surname'),
            type=GENERAL_PRACTICE_USER,
            is_staff=True,
        )
        gp_user_data = {
            'user': gp_manager_user,
            'role': GeneralPracticeUser.PRACTICE_MANAGER,
            'telephone_mobile': self.cleaned_data.get('telephone_mobile'),
            'telephone_code': self.cleaned_data.get('telephone_code'),
            'title': self.cleaned_data.get('title')
        }
        if gp_organisation:
            gp_user_data['organisation'] = gp_organisation
        general_practice_user = GeneralPracticeUser.objects.create(**gp_user_data)

        return {
            'general_pratice_user': general_practice_user,
            'password': gp_manager_user.password
        }


class NewGPForm(forms.ModelForm):

    title = forms.ChoiceField(choices=TITLE_CHOICE, required=True, label='')
    first_name = forms.CharField(max_length=255, required=True, label='', widget=forms.TextInput())
    last_name = forms.CharField(max_length=255, required=True, label='', widget=forms.TextInput())
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': ''}),
                             help_text='The email address will be the username ' + \
                                        'when your user logs into eMR. ' + \
                                        'Please note that usernames are case sensitive.',
                             label='',
                             required=True)
    username = forms.CharField(max_length=255, required=False, label='', widget=forms.TextInput())
    password = forms.CharField(required=True, widget=forms.HiddenInput())
    send_email = forms.BooleanField(required=False, initial=False)
    telephone_mobile = forms.CharField(required=True)
    telephone_code = forms.CharField(required=True, widget=forms.HiddenInput())

    class Meta:
        model = GeneralPracticeUser
        fields = ('first_name', 'last_name', 'title', 'email', 'username', 'password', 'send_email', 'role', 'payment_bank_holder_name',
                    'payment_bank_account_number', 'payment_bank_sort_code', 'telephone_mobile' ,'telephone_code')
        widgets = {
            'payment_bank_sort_code': forms.HiddenInput(attrs={'placeholder': '', }),
            'payment_bank_holder_name': forms.HiddenInput(),
            'payment_bank_account_number': forms.HiddenInput()
        }
        labels = {
            'payment_bank_holder_name': '',
            'payment_bank_account_number': '',
            'payment_bank_sort_code': ''
        }


class NewClientForm(forms.ModelForm):

    title = forms.ChoiceField(choices=TITLE_CHOICE, required=True, label='')
    first_name = forms.CharField(max_length=255, required=True, label='', widget=forms.TextInput())
    last_name = forms.CharField(max_length=255, required=True, label='', widget=forms.TextInput())
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': ''}),
                             help_text='The email address will be the username ' + \
                                        'when your user logs into eMR. ' + \
                                        'Please note that usernames are case sensitive.',
                             label='',
                             required=True)
    username = forms.CharField(max_length=255, required=False, label='', widget=forms.TextInput())
    password = forms.CharField(required=True, widget=forms.HiddenInput())
    send_email = forms.BooleanField(required=False, initial=False)
    telephone_mobile = forms.CharField(required=True)
    telephone_code = forms.CharField(required=True, widget=forms.HiddenInput())

    class Meta:
        model = ClientUser
        fields = (
            'first_name', 'last_name', 'title', 'email',
            'username', 'password', 'send_email',
            'telephone_mobile', 'telephone_code'
        )


class PracticePreferencesForm(forms.ModelForm):
    notification = forms.ChoiceField(choices=NOTIFICATIONS, required=False)
    contact_feedback = forms.BooleanField(required=False)
    contact_updates = forms.BooleanField(required=False)

    class Meta:
        model = PracticePreferences
        fields = ('notification', 'contact_feedback', 'contact_updates')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class NewMediForm(forms.ModelForm):

    first_name = forms.CharField(max_length=255, required=True, label='', widget=forms.TextInput())
    last_name = forms.CharField(max_length=255, required=True, label='', widget=forms.TextInput())
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': ''}), label='', required=True)
    username = forms.CharField(max_length=255, required=True, label='', widget=forms.TextInput())
    password = forms.CharField(required=True, widget=forms.HiddenInput())
    send_email = forms.BooleanField(required=False, initial=False)

    class Meta:
        model = MedidataUser
        fields = ('first_name', 'last_name', 'email', 'username', 'password', 'send_email')


class AllUserForm(forms.Form):

    USER_TYPE=(
        (MEDIDATA_USER, 'Medidata'),
        (CLIENT_USER, 'Client'),
        (GENERAL_PRACTICE_USER, 'General Practice')
    )

    user_type = forms.ChoiceField(choices=USER_TYPE, label='', required=True)
    first_name = forms.CharField(max_length=255, required=True, label='', widget=forms.TextInput())
    last_name = forms.CharField(max_length=255, required=True, label='', widget=forms.TextInput())
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': ''}), label='', required=True)
    username = forms.CharField(max_length=255, required=True, label='', widget=forms.TextInput())
    password = forms.CharField(required=False, widget=forms.HiddenInput())
    send_email = forms.BooleanField(required=False, initial=False)
    role = forms.CharField(max_length=255, label='', required=False, widget=forms.HiddenInput())
    payment_bank_account_number = forms.CharField(
            max_length=255, required=False,
            label='', widget=forms.TextInput()
    )
    payment_bank_holder_name = forms.CharField(
            max_length=255, required=False,
            label='', widget=forms.TextInput()
    )
    payment_bank_sort_code = forms.CharField(
            max_length=255, required=False,
            label='', widget=forms.HiddenInput()
    )
    gp_organisation = forms.ModelChoiceField(
            queryset=OrganisationGeneralPractice.objects.all(), required=False,
            label='', widget=forms.Select(attrs={'class': 'organisations'})
    )
    client_organisation = forms.ModelChoiceField(
            queryset=OrganisationClient.objects.all(), required=False,
            label='', widget=forms.Select(attrs={'class': 'organisations'})
    )
    medi_organisation = forms.ModelChoiceField(
            queryset=OrganisationMedidata.objects.all(), required=False,
            label='', widget=forms.Select(attrs={'class': 'organisations'})
    )


class TwoFactorForm(forms.Form):
    username = forms.CharField(widget=forms.HiddenInput())
    password = forms.CharField(widget=forms.HiddenInput())
    opt_id = forms.CharField(max_length=255, widget=forms.HiddenInput())
    pin = forms.CharField(max_length=10, label="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('initial'):
            user = kwargs['initial'].get('user')
            if user and hasattr(user, 'userprofilebase'):
                response = AuthMobile(number=user.userprofilebase.get_telephone_e164()).request()
                if response.status_code == 200:
                    response_results_dict = json.loads(response.text)
                    self.fields['opt_id'].initial = response_results_dict['id']

    def is_valid(self):
        valid = super().is_valid()
        if valid:
            data = self.cleaned_data
            response = AuthMobile(mobi_id=data['opt_id'], pin=data['pin']).verify()
            if response.status_code == 200:
                response_results_dict = json.loads(response.text)
                if not response_results_dict['validated']:
                    self._errors = {"__all__": ["OTP isn't valid."]}
                    return False
        return valid


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('instance'):
            user = kwargs['instance']
            if not user.has_perm('accounts.change_user'):
                self.fields['first_name'].widget.attrs['disabled'] = True
                self.fields['last_name'].widget.attrs['disabled'] = True
                self.fields['email'].widget.attrs['disabled'] = True


class UserProfileBaseForm(forms.ModelForm):
    class Meta:
        model = UserProfileBase
        fields = ('telephone_mobile', 'telephone_code')
        widgets = {
            'telephone_code': forms.HiddenInput(attrs={'placeholder': '', })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('instance'):
            userprofile = kwargs['instance']
            if userprofile.user and not userprofile.user.has_perm('accounts.change_user'):
                self.fields['telephone_mobile'].widget.attrs['disabled'] = True
                self.fields['telephone_code'].widget.attrs['disabled'] = True


class BankDetailsForm(forms.ModelForm):
    payment_bank_holder_name = forms.CharField(max_length=255, required=False, label='', widget=forms.TextInput())
    payment_bank_account_number = forms.CharField(max_length=8, min_length=8, required=False, label='', widget=forms.TextInput())
    payment_bank_sort_code = forms.CharField(max_length=6, min_length=6, required=False, label='', widget=forms.TextInput())

    class Meta:
        model = OrganisationGeneralPractice
        fields = ('payment_bank_holder_name', 'payment_bank_account_number', 'payment_bank_sort_code')


class CustomLoginForm(AuthenticationForm):
    def clean(self):
        error_messages = '"%(username)s"' + " can't access in this site."
        super().clean()
        user = self.get_user()
        if user.type == PATIENT_USER:
            error_messages = 'This site is not available for patient user'
            raise forms.ValidationError(
                error_messages
            )
        elif not user.is_superuser:
            site = self.request.get_host()
            access_control = SiteAccessControl.objects.filter(site_host=site).first()
            access_permission = access_control.can_access_site(user_type=user.type)
            if access_permission:
                return self.cleaned_data
            else:
                raise forms.ValidationError(
                    error_messages,
                    params={'username': self.cleaned_data['username']}
                ) 
        else:
            return self.cleaned_data


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(CustomAuthenticationForm, self).__init__(*args, **kwargs)

        self.fields['username'].help_text = '<h6 class="float-left mb-3">Please note that the email field is case sensitive.</h6>'