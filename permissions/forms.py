from django import forms
from permissions.models import InstructionPermission
from instructions.models import Instruction
from accounts.models import GeneralPracticeUser
from django.db.models import Q
from permissions.model_choices import MANAGER_PERMISSIONS, \
                                      OTHER_PERMISSIONS, \
                                      GP_PERMISSIONS
from django.contrib.auth.models import Permission, Group


exclude_permission = (
    'add_instruction',
    'change_instruction',
    'delete_instruction',
)


class MyModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return "%s" % obj.name


class InstructionPermissionForm(forms.ModelForm):
    permissions = MyModelMultipleChoiceField(
        Permission.objects.filter(
                Q(content_type__model = Instruction._meta.model_name) |
                Q(codename__in = MANAGER_PERMISSIONS + OTHER_PERMISSIONS + GP_PERMISSIONS)
            ).exclude(codename__in = exclude_permission),
        widget = forms.CheckboxSelectMultiple(attrs = {'class': 'list-permissions'}),
        required = False
    )

    class Meta:
        model = InstructionPermission
        fields = ('__all__')
        widgets = {
            'organisation': forms.HiddenInput(),
            'role': forms.Select(attrs={'disabled': 'true', 'class': 'permission-role'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if kwargs.get('instance') and kwargs['instance'].group:
            fixed_permissions = Permission.objects.none()

            if kwargs['instance'].role == GeneralPracticeUser.PRACTICE_MANAGER:
                fixed_permissions = Permission.objects.filter(
                    codename__in = MANAGER_PERMISSIONS)
            elif kwargs['instance'].role == GeneralPracticeUser.GENERAL_PRACTICE:
                fixed_permissions = Permission.objects.filter(
                    codename__in = GP_PERMISSIONS)
            else:
                fixed_permissions = Permission.objects.filter(
                    codename__in = OTHER_PERMISSIONS)
            self.initial['permissions'] = kwargs['instance'].group.permissions.all() | fixed_permissions


class GroupPermissionForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ('__all__')
