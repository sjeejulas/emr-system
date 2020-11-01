from django.db import models
from organisations.models import OrganisationClient
from snomedct.models import CommonSnomedConcepts, SnomedConcept
from accounts.models import ClientUser
from common.models import TimeStampedModel


class TemplateInstruction(TimeStampedModel, models.Model):
    template_title = models.CharField(max_length=255)
    description = models.TextField(max_length=255, blank=True, null=True)
    organisation = models.ForeignKey(OrganisationClient, null=True, on_delete=models.CASCADE, blank=True)
    created_by = models.ForeignKey(ClientUser, on_delete=models.CASCADE, null=True, blank=True)
    common_snomed_concepts = models.ManyToManyField(CommonSnomedConcepts)

    class Meta:
        verbose_name = 'Template of Instruction'

    def __str__(self):
        return self.template_title


class TemplateAdditionalQuestion(models.Model):
    template_instruction = models.ForeignKey(TemplateInstruction, on_delete=models.CASCADE, related_name='questions')
    question = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Template Instruction Additional Question'

    def __str__(self):
        return self.question


class TemplateAdditionalCondition(models.Model):
    template_instruction = models.ForeignKey(TemplateInstruction, on_delete=models.CASCADE, related_name='conditions')
    snomedct = models.ForeignKey(SnomedConcept, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Template Instruction Additional Condition'

    def __str__(self):
        return self.snomedct.__str__()
