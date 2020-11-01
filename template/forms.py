from django import forms
from .models import TemplateInstruction, TemplateAdditionalQuestion, TemplateAdditionalCondition
from snomedct.models import CommonSnomedConcepts
from instructions.forms import MyMultipleChoiceField


class TemplateInstructionForm(forms.ModelForm):
    addition_condition = MyMultipleChoiceField(required=False)

    class Meta:
        model = TemplateInstruction
        fields = ('template_title', 'description', 'common_snomed_concepts', 'addition_condition')
        widgets = {
            'common_snomed_concepts': forms.CheckboxSelectMultiple()
        }


class TemplateQuestionForm(forms.ModelForm):
    class Meta:
        model = TemplateAdditionalQuestion
        fields = ('__all__')
        widgets={
            'question': forms.TextInput(attrs={'class': 'form-control questions_inputs'}),
            'template_instruction': forms.HiddenInput()
        }


class TemplateConditionForm(forms.ModelForm):
    class Meta:
        model = TemplateAdditionalCondition
        fields = ('__all__')
