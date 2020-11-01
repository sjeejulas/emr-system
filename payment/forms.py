from django import forms
from django.utils.html import format_html
from django.db.models import Q

from .models import OrganisationFeeRate, InstructionVolumeFee
from common.functions import get_url_page


class OrganisationFeeForm(forms.ModelForm):
    max_day_lvl_4 = forms.IntegerField(required=False, label='Lowest payment band after day:', widget=forms.NumberInput(attrs={'class': 'vIntegerField'}))

    class Meta:
        model = OrganisationFeeRate
        fields = '__all__'

    def clean(self):
        try:
            self.cleaned_data['max_day_lvl_4'] = self.cleaned_data['max_day_lvl_3'] + 1
            if self.cleaned_data['max_day_lvl_1'] >= self.cleaned_data['max_day_lvl_2'] \
                    or self.cleaned_data['max_day_lvl_1'] >= self.cleaned_data['max_day_lvl_3'] \
                    or self.cleaned_data['max_day_lvl_1'] >= self.cleaned_data['max_day_lvl_4']:
                raise forms.ValidationError("Day are incorrect: First day Must be minimum.")

            if self.cleaned_data['max_day_lvl_2'] >= self.cleaned_data['max_day_lvl_3'] \
                    or self.cleaned_data['max_day_lvl_2'] >= self.cleaned_data['max_day_lvl_4']:
                raise forms.ValidationError("Day are incorrect: Invalid max day lvl 2")

            if self.cleaned_data['max_day_lvl_3'] >= self.cleaned_data['max_day_lvl_4']:
                raise forms.ValidationError("Day are incorrect: Max day lvl 4 must more than Max day lvl 3")

            organisation_gp = self.cleaned_data['gp_practice']
            organisation_fee = OrganisationFeeRate.objects.filter(gp_practice=organisation_gp).first()
            owning_gp = ''
            if self.initial:
                owning_gp = self.initial['gp_practice']

            if owning_gp:
                if organisation_fee and organisation_gp.pk != owning_gp:
                    raise forms.ValidationError(
                        format_html(
                            '<strong>Organisation had selected:</strong> <a href="{gp_payment_fee_edit_path}">Here</a>'.format(
                                gp_payment_fee_edit_path=get_url_page('admin_gp_payment_fee_edit', organisation_fee.pk)
                            )
                        )
                    )
            else:
                if organisation_fee:
                    raise forms.ValidationError(
                        format_html(
                            '<strong>Organisation had selected:</strong> <a href="{gp_payment_fee_edit_path}">Here</a>'.format(
                                gp_payment_fee_edit_path=get_url_page('admin_gp_payment_fee_edit', organisation_fee.pk)
                            )
                        )
                    )

            return self.cleaned_data
        except KeyError:
            self._errors


class InstructionVolumeFeeForm(forms.ModelForm):

    class Meta:
        model = InstructionVolumeFee
        fields = '__all__'

    def clean(self):
        try:
            if self.cleaned_data['max_volume_band_lowest'] >= self.cleaned_data['max_volume_band_low'] \
                    or self.cleaned_data['max_volume_band_lowest'] >= self.cleaned_data['max_volume_band_medium'] \
                    or self.cleaned_data['max_volume_band_lowest'] >= self.cleaned_data['max_volume_band_high'] \
                    or self.cleaned_data['max_volume_band_lowest'] >= self.cleaned_data['max_volume_band_top']:
                raise forms.ValidationError("Invalid band value: Lowest band must be minimum.")

            if self.cleaned_data['max_volume_band_low'] >= self.cleaned_data['max_volume_band_medium'] \
                    or self.cleaned_data['max_volume_band_low'] >= self.cleaned_data['max_volume_band_high'] \
                    or self.cleaned_data['max_volume_band_low'] >= self.cleaned_data['max_volume_band_top']:
                raise forms.ValidationError("Invalid band value: Invalid low band")

            if self.cleaned_data['max_volume_band_medium'] >= self.cleaned_data['max_volume_band_high']:
                raise forms.ValidationError("Invalid band value: High band value must more than medium band value")

            if self.cleaned_data['max_volume_band_high'] >= self.cleaned_data['max_volume_band_top']:
                raise forms.ValidationError("Invalid band value: Top band value must more than high band value")

            owning_client = ''
            all_fee_types = []
            if self.initial:
                owning_client = self.initial['client_org']
                all_fee_types = InstructionVolumeFee.objects.filter(
                    ~Q(fee_rate_type=self.initial['fee_rate_type']), client_org=owning_client
                ).values_list('fee_rate_type', flat=True)

            organisation_client = self.cleaned_data['client_org']
            org_fee_type = self.cleaned_data['fee_rate_type']
            organisation_fee = InstructionVolumeFee.objects.filter(
                client_org=organisation_client, fee_rate_type=org_fee_type
            ).first()

            if owning_client:
                if organisation_client.pk == owning_client:
                    if self.cleaned_data['fee_rate_type'] in all_fee_types:
                        raise forms.ValidationError(
                            format_html('<strong>{rate_type} type had been selected:</strong>'.format(
                                rate_type=organisation_fee.get_fee_rate_type_display(),
                                client_org=organisation_fee.client_org
                            )))
            elif organisation_fee:
                raise forms.ValidationError(format_html('<strong>{rate_type} type of {client_org} had been selected:</strong>'.format(
                    rate_type=organisation_fee.get_fee_rate_type_display(),
                    client_org=organisation_fee.client_org
                )))

            return self.cleaned_data
        except KeyError:
            self._errors