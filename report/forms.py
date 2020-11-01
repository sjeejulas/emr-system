from django import forms

from .models import ThirdPartyAuthorisation

import datetime
import uuid


class AccessCodeForm(forms.Form):
    access_code = forms.CharField(max_length=12, required=False)


class ThirdPartyAuthorisationForm(forms.ModelForm):
    error_messages = {
        'email_mismatch': "The two email fields didn't match.",
        'phone_number_both_input': "Please enter either office phone or mobile phone only"
    }

    email_1 = forms.EmailField()
    email_2 = forms.EmailField()

    class Meta:
        model = ThirdPartyAuthorisation
        exclude = ('email', 'patient_report_auth', 'count', 'expired_date')
        widgets = {
            'family_phone_number_code': forms.HiddenInput(attrs={'placeholder': ''}),
            'office_phone_number_code': forms.HiddenInput(attrs={'placeholder': ''})
        }

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
        family_phone_number = self.cleaned_data.get("family_phone_number")
        office_phone_number = self.cleaned_data.get("office_phone_number")
        if family_phone_number and office_phone_number:
            raise forms.ValidationError(
                self.error_messages['phone_number_both_input'],
            )

        if not family_phone_number and  not office_phone_number:
            raise forms.ValidationError(
                self.error_messages['phone_number_both_input'],
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
