from django.db import models
from django.contrib.postgres.fields import JSONField
from instructions.models import Instruction
from instructions.model_choices import INSTRUCTION_STATUS_COMPLETE
from snomedct.models import SnomedConcept, ReadCode
from accounts.models import User, GeneralPracticeUser
from postgres_copy import CopyManager
from django.utils.html import format_html
from common.functions import get_env_variable, aes_with_salt_encryption, aes_with_salt_decryption

import random, string


class AmendmentsForRecord(models.Model):
    REDACTION_STATUS_NEW = 'NEW'
    REDACTION_STATUS_DRAFT = 'DRAFT'
    REDACTION_STATUS_SUBMIT = 'SUBMIT'

    REDACTION_STATUS_CHOICES = (
        (REDACTION_STATUS_NEW, 'New'),
        (REDACTION_STATUS_DRAFT, 'Draft'),
        (REDACTION_STATUS_SUBMIT, 'Submit')
    )

    PREPARED_AND_SIGNED = 'PREPARED_AND_SIGNED'
    PREPARED_AND_REVIEWED = 'PREPARED_AND_REVIEWED'

    SUBMIT_OPTION_CHOICES = (
        (PREPARED_AND_SIGNED, 'Prepared and signed directly by {}'),
        (PREPARED_AND_REVIEWED, format_html('Signed off by <span id="preparer"></span>')),
    )

    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE)
    consultation_notes = models.TextField(blank=True)
    acute_prescription_notes = models.TextField(blank=True)
    repeat_prescription_notes = models.TextField(blank=True)
    referral_notes = models.TextField(blank=True)
    significant_problem_notes = models.TextField(blank=True)
    attachment_notes = models.TextField(blank=True)
    bloods_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    redacted_xpaths = JSONField(null=True)
    re_redacted_codes = JSONField(null=True)
    submit_choice = models.CharField(max_length=255, choices=SUBMIT_OPTION_CHOICES, blank=True)
    review_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    prepared_by = models.ForeignKey(GeneralPracticeUser, on_delete=models.CASCADE, null=True)
    status = models.CharField(choices=REDACTION_STATUS_CHOICES, max_length=6, default=REDACTION_STATUS_NEW)
    comment_notes = models.TextField(blank=True)
    instruction_checked = models.BooleanField(default=False, blank=True, null=True)

    _raw_medical_xml_encrypted = models.TextField(blank=True)
    _raw_medical_xml_aes_key = models.CharField(max_length=255, blank=True)
    raw_medical_xml_salt_and_encrypted_iv = models.CharField(max_length=255, blank=True)
    raw_medical_xml_aes_key_salt_and_encrypted_iv = models.CharField(max_length=255, blank=True)

    @property
    def patient_emis_number(self) -> str:
        return self.instruction.patient_information.patient_emis_number

    def get_gp_name(self) -> str:
        gp_name = ''
        if self.instruction.status == INSTRUCTION_STATUS_COMPLETE:
            if self.prepared_by:
                gp_name = self.prepared_by
        return gp_name

    def additional_acute_medications(self):
        return AdditionalMedicationRecords.objects.filter(amendments_for_record=self.id, repeat=False)

    def additional_repeat_medications(self):
        return AdditionalMedicationRecords.objects.filter(amendments_for_record=self.id, repeat=True)

    def additional_allergies(self):
        return AdditionalAllergies.objects.filter(amendments_for_record=self.id)

    def redacted(self, xpaths) -> bool:
        if self.redacted_xpaths is not None:
            return all(xpath in self.redacted_xpaths for xpath in xpaths)
        else:
            return False

    def set_raw_medical_xml_aes_key(self, val: str) -> None:
        salt = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        iv_salt, iv_aes_key, ciphertext = aes_with_salt_encryption(val, salt)
        self.raw_medical_xml_aes_key_salt_and_encrypted_iv = '{iv_salt}${iv_aes_key}'.format(
            iv_salt=iv_salt, iv_aes_key=iv_aes_key
        )
        self._raw_medical_xml_aes_key = '{salt}${aes_ciphertext}'.format(
            salt=salt, aes_ciphertext=ciphertext
        )

    def get_raw_medical_xml_aes_key(self) -> str:
        if self.raw_medical_xml_aes_key_salt_and_encrypted_iv:
            return aes_with_salt_decryption(
                self._raw_medical_xml_aes_key,
                self.raw_medical_xml_aes_key_salt_and_encrypted_iv,
            )
        return self._raw_medical_xml_aes_key

    raw_medical_xml_aes_key = property(
        get_raw_medical_xml_aes_key,
        set_raw_medical_xml_aes_key
    )

    def set_raw_medical_xml(self, val: str) -> None:
        salt = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        iv_salt, iv_aes_key, ciphertext = aes_with_salt_encryption(val, salt, self.raw_medical_xml_aes_key)
        self.raw_medical_xml_salt_and_encrypted_iv = '{iv_salt}${iv_aes_key}'.format(
            iv_salt=iv_salt, iv_aes_key=iv_aes_key
        )
        self._raw_medical_xml_encrypted = '{salt}${aes_ciphertext}'.format(
            salt=salt, aes_ciphertext=ciphertext
        )

    def get_raw_medical_xml(self) -> str:
        if self.raw_medical_xml_salt_and_encrypted_iv:
            return aes_with_salt_decryption(
                self._raw_medical_xml_encrypted,
                self.raw_medical_xml_salt_and_encrypted_iv,
                self.raw_medical_xml_aes_key
            )
        return self._raw_medical_xml_encrypted

    raw_medical_xml_encrypted = property(
        get_raw_medical_xml,
        set_raw_medical_xml
    )


class AdditionalMedicationRecords(models.Model):
    drug = models.CharField(max_length=255)
    dose = models.CharField(max_length=255)
    frequency = models.CharField(max_length=255)
    snomed_concept = models.ForeignKey(SnomedConcept, on_delete=models.CASCADE, null=True)
    amendments_for_record = models.ForeignKey(AmendmentsForRecord, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    prescribed_from = models.DateField(null=True)
    prescribed_to = models.DateField(null=True)
    notes = models.TextField()
    repeat = models.BooleanField()


class AdditionalAllergies(models.Model):
    allergen = models.CharField(max_length=255)
    reaction = models.CharField(max_length=255)
    date_discovered = models.DateField(null=True)
    amendments_for_record = models.ForeignKey(AmendmentsForRecord, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NhsSensitiveConditions(models.Model):
    group = models.CharField(max_length=128)
    snome_code = models.CharField(max_length=128)

    @staticmethod
    def get_sensitives_readcode():
        sensitive_readcode = set()
        sensitive_snome = NhsSensitiveConditions.objects.all().values_list('snome_code', flat=True)
        for snome in sensitive_snome:
            for r in ReadCode.objects.filter(concept_id=snome):
                sensitive_readcode.add(r.ext_read_code)
        return sensitive_readcode


class ReferencePhrases(models.Model):
    name = models.CharField(max_length=255)
    objects = CopyManager()

    def __str__(self):
        return self.name


class RedactedAttachment(models.Model):
    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE)
    dds_identifier = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    raw_attachment_file_content = models.BinaryField()
    attachment_file = models.FileField(upload_to='medical_attachments', null=True, blank=True)
    redacted_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    def make_attachment_file(self):
        pass
