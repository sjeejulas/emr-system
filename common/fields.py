from django import forms
from django.core.exceptions import ValidationError


class MyChoiceField(forms.ChoiceField):

    def validate(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages['required'], code='required')
