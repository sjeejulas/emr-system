from django import forms
from .models import OrganisationGeneralPractice


class GeneralPracticeForm(forms.Form):
    gp_practice = forms.ModelChoiceField(queryset=OrganisationGeneralPractice.objects.none())

    class Meta:
        model = OrganisationGeneralPractice
        fields = ('nhs')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial_data = kwargs.get('initial')
        if initial_data:
            gp_practice = initial_data.get('gp_practice')
            if gp_practice:
                self.fields['gp_practice'] = forms.CharField(max_length=255)
