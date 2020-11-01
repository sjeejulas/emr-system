from django import forms
from permissions.templatetags.get_permissions import process_instruction
from permissions.models import InstructionPermission
from .models import AmendmentsForRecord
from instructions.models import Instruction
from instructions.model_choices import AMRA_TYPE
from organisations.models import OrganisationGeneralPractice
from accounts.models import User, GeneralPracticeUser, UserProfileBase
from accounts import models
from typing import List


class MedicalReportFinaliseSubmitForm(forms.Form):
    prepared_by = forms.ModelChoiceField(
        queryset=GeneralPracticeUser.objects.all()
    )
    instruction_checked = forms.BooleanField(required=False, initial=False, label='')
    prepared_and_signed = forms.ChoiceField(choices=AmendmentsForRecord.SUBMIT_OPTION_CHOICES,
                                            widget=forms.RadioSelect(attrs={'class': 'finaliseChoice'}),
                                            required=False,
                                            )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = GeneralPracticeUser.objects.all()
        if kwargs:
            submit_options = kwargs.get('initial').get('SUBMIT_OPTION_CHOICES')
            if submit_options:
                self.fields['prepared_and_signed'].choices = submit_options
            record_type = kwargs.get('initial').get('record_type')
            if record_type and record_type == 'AMRA':
                queryset = queryset.filter(user__groups__permissions__codename='sign_off_amra')
            if record_type and record_type == 'SARS':
                queryset = queryset.filter(user__groups__permissions__codename='sign_off_sars')
        if user:
            queryset = queryset.filter(organisation=user.userprofilebase.generalpracticeuser.organisation)
        self.fields['prepared_by'].queryset = queryset

    def is_valid(self, post_data):
        super().is_valid()
        error_message = "The report was not submitted. Please review your answers and save the report. " \
                        "If the problem persists please contact your MediData representative."

        if post_data['event_flag'] == 'submit' and 'prepared_and_signed' not in post_data:
            self._errors = error_message
            return False

        if 'prepared_and_signed' in post_data:
            if post_data['prepared_and_signed'] == 'PREPARED_AND_REVIEWED' and not post_data['prepared_by']:
                self._errors = error_message
                return False

        return True

    def clean(self):
        super().clean()
        if self.cleaned_data.get('prepared_and_signed') == 'PREPARED_AND_SIGNED':
            self.cleaned_data['prepared_by'] = ''

        return self.cleaned_data


class AllocateInstructionForm(forms.Form):
    PROCEED_REPORT = 0
    RETURN_TO_PIPELINE = 1
    ALLOCATE_OPTIONS_CHOICE = (
        (PROCEED_REPORT, 'Proceed with report'),
        (RETURN_TO_PIPELINE, 'Return to pipeline view')
    )
    allocate_options = forms.ChoiceField(choices=ALLOCATE_OPTIONS_CHOICE, widget=forms.RadioSelect())
    gp_practitioner = forms.ModelChoiceField(queryset=None, required=False)

    def __init__(self, user=None, instruction_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.type == models.GENERAL_PRACTICE_USER:
            organisation = user.userprofilebase.generalpracticeuser.organisation
            profiles = UserProfileBase.all_objects.all()
            role = []
            if instruction_id:
                role = self.set_role_can_precess(instruction_id, organisation)
            queryset = User.objects.filter(
                userprofilebase__in=profiles.alive(),
                userprofilebase__generalpracticeuser__organisation=organisation,
                userprofilebase__generalpracticeuser__role__in=role,
            )
            queryset = queryset.exclude(userprofilebase__generalpracticeuser__role=GeneralPracticeUser.PRACTICE_MANAGER)
            self.fields['gp_practitioner'] = forms.ModelChoiceField(queryset,
                                                                    required=False)
            if user and instruction_id:
                self.fields['allocate_options'] = self.set_allocate_by_permission(user, instruction_id, queryset)

    def set_allocate_by_permission(self, user: User, instruction_id: str, queryset) -> forms.ChoiceField:
        can_proceed = process_instruction(user.id, instruction_id)
        ALLOCATE_OPTIONS_CHOICE = [(self.RETURN_TO_PIPELINE, 'Return to pipeline view')]
        if not user.has_perm('instructions.allocate_gp'):
            self.fields['gp_practitioner'] = forms.ModelChoiceField(queryset, required=False, widget=forms.HiddenInput())
        if can_proceed:
            ALLOCATE_OPTIONS_CHOICE.append((self.PROCEED_REPORT, 'Proceed with report'))
        return forms.ChoiceField(choices=ALLOCATE_OPTIONS_CHOICE, widget=forms.RadioSelect())

    def set_role_can_precess(self, instruction_id: str, organisation: OrganisationGeneralPractice) -> List[int]:
        role = []
        instruction = Instruction.objects.get(pk=instruction_id)
        for permission in InstructionPermission.objects.filter(organisation=organisation):
            if instruction.type == AMRA_TYPE:
                if permission.group and permission.group.permissions.filter(codename='process_amra').exists():
                    role.append(permission.role)
            else:
                if permission.group and permission.group.permissions.filter(codename='process_sars').exists():
                    role.append(permission.role)
        return role
