from django.db import models
from common.models import TimeStampedModel
from organisations.models import OrganisationGeneralPractice
from instructions.models import Instruction


class Library(TimeStampedModel):
    gp_practice = models.ForeignKey(OrganisationGeneralPractice, on_delete=models.CASCADE)
    key = models.CharField(max_length=255, verbose_name='Text')
    value = models.CharField(max_length=255, blank=True, verbose_name='Replaced by')

    def __str__(self):
        return self.key + ': ' + self.value

    class Meta:
        verbose_name = 'Library'
        verbose_name_plural = 'Libraries'
        ordering = ('-created', )


class LibraryHistory(TimeStampedModel):
    ACTION_REPLACE              = 0
    ACTION_REPLACE_ALL          = 1
    ACTION_LINE_REDACT          = 2
    ACTION_HIGHLIGHT_REDACT     = 3
    ACTION_REMOVE_LINE_REDACT   = 4

    ACTION_CHOICES = (
        (ACTION_REPLACE, 'Replace'),
        (ACTION_REPLACE_ALL, 'Replace All'),
        (ACTION_LINE_REDACT, 'Line Redact'),
        (ACTION_HIGHLIGHT_REDACT, 'Highlight Black'),
        (ACTION_REMOVE_LINE_REDACT, 'Remove Line Redact')
    )

    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE)
    action = models.IntegerField(choices=ACTION_CHOICES)
    old = models.CharField(max_length=255, blank=True, verbose_name='Old value')
    new = models.CharField(max_length=255, blank=True, verbose_name='New value')
    guid = models.CharField(max_length=255, blank=True, verbose_name='Guid')
    section = models.CharField(max_length=30, blank=True, verbose_name='Medical Redaction Section')
    index = models.PositiveIntegerField(null=True)
    xpath = models.CharField(max_length=255, blank=True)
