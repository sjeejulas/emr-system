from django import forms
from django.forms.models import modelformset_factory
from django.core.exceptions import ValidationError

from .models import Library


class LibraryForm(forms.ModelForm):
    class Meta:
        model = Library
        fields = ('key', 'value')

    def __init__(self, *args, **kwargs):
        self.gp_org_id = kwargs.pop('gp_org_id')
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['key'] = (cleaned_data['key'].strip()).replace(',', '')
        if self.gp_org_id and Library.objects.filter(gp_practice=self.gp_org_id, key__iexact=cleaned_data['key']).exists():
            raise ValidationError(
                'This word already exists in your library. If you wish to edit it, please go back to the Library and edit from there'
            )
        return cleaned_data


LibraryFormset = modelformset_factory(
    Library,
    form=LibraryForm
)