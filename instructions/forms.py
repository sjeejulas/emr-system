import uuid
import datetime

from django import forms
from django.forms.models import modelformset_factory
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q
from django_clamd.validators import validate_file_infection
from instructions.model_choices import AMRA_TYPE, SARS_TYPE
from .models import InstructionAdditionQuestion, Instruction, InstructionClientNote, ClientNote
from template.models import TemplateInstruction
from common.functions import multi_getattr
from snomedct.models import CommonSnomedConcepts
from report.models import ThirdPartyAuthorisation


DATE_INPUT_FORMATS = settings.DATE_INPUT_FORMATS


class MyMultipleChoiceField(forms.MultipleChoiceField):

    def validate(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages['required'], code='required')


class ReferenceForm(forms.ModelForm):
    medi_ref = forms.IntegerField(widget=forms.TextInput(attrs={'readonly':'readonly'}))
    class Meta:
        model = Instruction
        fields = ('your_ref',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['medi_ref'].initial = self.instance.medi_ref
        else:
            next_number = 1
            if Instruction.objects.all().exists():
                next_number = Instruction.objects.order_by('pk').last().pk + 1
            self.fields['medi_ref'].initial = settings.MEDI_REF_NUMBER + next_number


class ScopeInstructionForm(forms.Form):
    type = forms.ChoiceField(choices=[], widget=forms.RadioSelect(attrs={'class': 'd-inline instructionType'}))
    template = forms.ModelChoiceField(queryset=TemplateInstruction.objects.filter(organisation__isnull=True), required=False)
    common_condition = forms.MultipleChoiceField(choices=[], widget=forms.CheckboxSelectMultiple(), required=False)
    addition_condition = MyMultipleChoiceField(required=False)
    addition_condition_title = forms.CharField(required=False, widget=forms.HiddenInput())
    consent_form = forms.FileField(required=False, validators=[validate_file_infection])
    send_to_patient = forms.BooleanField(widget=forms.CheckboxInput(), label='Send copy of medical report to patient?', required=False)

    def __init__(self, user=None, patient_email=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.type == 'CLT':
            self.fields['date_range_from'] = forms.DateField(input_formats=DATE_INPUT_FORMATS, required=False,
                                                             widget=forms.DateInput(attrs={'autocomplete': 'off', 'placeholder': 'From'}))
            self.fields['date_range_to'] = forms.DateField(input_formats=DATE_INPUT_FORMATS, required=False,
                                                           widget=forms.DateInput(attrs={'autocomplete': 'off', 'placeholder': 'To'}))
        initial_data = kwargs.get('initial')
        if initial_data:
            self.fields['type'] = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'w-25'}))
        else:
            self.patient_email = patient_email
            FORM_INSTRUCTION_TYPE_CHOICES = []

            SCOPE_COMMON_CONDITION_CHOICES = [
                [[snomed.external_id for snomed in common_snomed.snomed_concept_code.all()], common_snomed.common_name] for common_snomed in CommonSnomedConcepts.objects.all()
            ]

            self.fields['common_condition'] = forms.MultipleChoiceField(choices=SCOPE_COMMON_CONDITION_CHOICES, widget=forms.CheckboxSelectMultiple(), required=False)

            if user:
                if user.can_do_under():
                    FORM_INSTRUCTION_TYPE_CHOICES.append((AMRA_TYPE, 'Underwriting(AMRA)'))
                if user.can_do_claim():
                    FORM_INSTRUCTION_TYPE_CHOICES.append((AMRA_TYPE, 'Claim(AMRA)'))
                if user.can_do_sars():
                    FORM_INSTRUCTION_TYPE_CHOICES.append((SARS_TYPE, 'SAR'))
            client_organisation = multi_getattr(user, 'userprofilebase.clientuser.organisation', default=None)
            if client_organisation:
                self.fields['template'] = forms.ModelChoiceField(
                        queryset=TemplateInstruction.objects.filter(
                            Q(organisation=client_organisation) | Q(organisation__isnull=True)),
                        required=False)

            self.fields['type'] = forms.ChoiceField(
                choices=FORM_INSTRUCTION_TYPE_CHOICES,
                widget=forms.RadioSelect(
                    attrs={'class': 'd-inline instructionType', 'id':'type'}
                )
            )

    def clean(self):
        super().clean()
        if not self.errors and not self.patient_email and not self.cleaned_data['consent_form']:
            raise ValidationError(
                "You must supply a valid consent form, " + \
                "or the patient's e-mail address when creating an %s instruction!" % \
                self.cleaned_data.get('type'))
        return self.cleaned_data


class AdditionQuestionForm(forms.ModelForm):
    class Meta:
        model = InstructionAdditionQuestion
        fields = ('question',)


AdditionQuestionFormset = modelformset_factory(
    InstructionAdditionQuestion,
    form=AdditionQuestionForm,
    fields=('question', ),
    extra=1,
    widgets={
        'question': forms.TextInput(attrs={'class': 'form-control questions_inputs'}, ),
    },
)


class ClientNoteForm(forms.ModelForm):
    class Meta:
        model = InstructionClientNote
        fields = ('__all__')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = []
        if self.instance:
            choices += [(self.instance.note, self.instance.note)]
        choices += [(obj.note, obj.note) for obj in ClientNote.objects.all()]
        self.fields['note'] = forms.ChoiceField(choices=choices)


class InstructionDateRangeForm(forms.ModelForm):
    date_range_from = forms.DateField(
        required=False, label="From",
        input_formats=settings.DATE_INPUT_FORMATS,
        widget=forms.DateInput(attrs={'autocomplete': "off"}))
    date_range_to = forms.DateField(
        required=False, label="To",
        input_formats=settings.DATE_INPUT_FORMATS,
        widget=forms.DateInput(attrs={'autocomplete': "off"}))

    class Meta:
        model = Instruction
        fields = ('date_range_from', 'date_range_to')


class ConsentForm(forms.ModelForm):
    consent_form = forms.FileField(required=False, label="Select a File", validators=[validate_file_infection])

    class Meta:
        model = Instruction
        fields = ('consent_form',)


class SarsConsentForm(forms.ModelForm):
    sars_consent = forms.FileField(required=False, label="Select a File", validators=[validate_file_infection])

    class Meta:
        model = Instruction
        fields = ('sars_consent',)


class MdxConsentForm(forms.ModelForm):
    mdx_consent = forms.FileField(required=False, validators=[validate_file_infection])

    class Meta:
        model = Instruction
        fields = ('mdx_consent',)


class InstructionAdminForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.fields.get('gp_user'):
            self.fields['gp_user'].required = False
        if self.fields.get('client_user'):
            self.fields['client_user'].required = False

    class Meta:
        model = Instruction
        fields = '__all__'


class DateRangeSearchForm(forms.Form):
    from_date = forms.DateField(
        input_formats=DATE_INPUT_FORMATS, required=False,
        widget=forms.DateInput(attrs={'autocomplete': 'off', 'placeholder': 'From'})
    )
    to_date = forms.DateField(
        input_formats=DATE_INPUT_FORMATS, required=False,
        widget=forms.DateInput(attrs={'autocomplete': 'off', 'placeholder': 'To'})
    )


class ConsentThirdParty(forms.ModelForm):
    error_messages = {
        'email_mismatch': "The two email fields didn't match.",
        'phone_number_input': "Please enter office phone"
    }

    email_1 = forms.EmailField()
    email_2 = forms.EmailField()

    class Meta:
        model = ThirdPartyAuthorisation
        exclude = ('email', 'patient_report_auth', 'count', 'expired_date')
        widgets = {
            'office_phone_number_code': forms.HiddenInput(attrs={'placeholder': ''})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('instance'):
            obj = kwargs['instance']
            self.fields['email_1'].initial = obj.email
            self.fields['email_2'].initial = obj.email

    def clean_email_2(self):
        email_1 = self.cleaned_data.get("email_1")
        email_2 = self.cleaned_data.get("email_2")
        if email_1 and email_2 and email_1 != email_2:
            raise forms.ValidationError(
                self.error_messages['email_mismatch'],
                code='email_mismatch',
            )
        return email_2

    def clean(self):
        super().clean()

        office_phone_number = self.cleaned_data.get("office_phone_number")

        if not office_phone_number:
            raise forms.ValidationError(
                self.error_messages['phone_number_input'],
            )

    def save(self, report_auth, commit=True):
        third_party = super().save(commit=False)
        third_party.patient_report_auth = report_auth
        third_party.email = self.cleaned_data['email_2']
        unique_url = uuid.uuid4().hex
        third_party.unique = unique_url

        third_party.expired_date = datetime.datetime.now().date() + datetime.timedelta(days=30)
        if third_party.modified:
            third_party.expired_date = third_party.modified + datetime.timedelta(days=30)

        if commit:
            third_party.save()

        return third_party
