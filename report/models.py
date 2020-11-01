from django.db import models
from common.models import TimeStampedModel
from accounts.models import Patient
from django.contrib.postgres.fields import ArrayField
from instructions.models import Instruction


class PatientReportAuth(TimeStampedModel):
    ACCESS_TYPE_PATIENT = 'patient'
    ACCESS_TYPE_THIRD_PARTY = 'third-party'

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, blank=True, null=True)
    instruction = models.ForeignKey('instructions.Instruction', on_delete=models.CASCADE)
    count = models.IntegerField(default=0)
    mobi_request_id = models.CharField(max_length=255, blank=True)
    locked_report = models.BooleanField(default=False)
    verify_pin = models.CharField(max_length=6, blank=True)
    url = models.CharField(max_length=256)
    report_de_activate = models.BooleanField(default=True)

    def __str__(self):
        return '%s : %s'%(self.instruction.__str__(), self.patient.__str__())


class ThirdPartyAuthorisation(TimeStampedModel):
    patient_report_auth = models.ForeignKey(PatientReportAuth, on_delete=models.CASCADE, related_name='third_parties', null=True)
    company = models.CharField(max_length=255, blank=True)
    contact_name = models.CharField(max_length=255)
    case_reference = models.CharField(max_length=255, blank=True)
    mobi_request_id = models.CharField(max_length=255, blank=True)
    mobi_request_voice_id = models.CharField(max_length=255, blank=True)
    count = models.IntegerField(default=0)
    locked_report = models.BooleanField(default=False)
    verify_sms_pin = models.CharField(max_length=6, blank=True)
    verify_voice_pin = models.CharField(max_length=6, blank=True)
    email = models.EmailField()
    family_phone_number_code = models.CharField(max_length=5, blank=True)
    family_phone_number = models.CharField(max_length=20, blank=True, null=True)
    office_phone_number_code = models.CharField(max_length=5, blank=True)
    office_phone_number = models.CharField(max_length=20, blank=True, null=True)
    expired_date = models.DateField(null=True)
    expired = models.BooleanField(default=False)
    unique = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.company

    def get_family_phone_e164(self) -> str:
        phone = self.get_phone_without_zero(self.family_phone_number)
        return "+{phone_code}{phone_number}".format(phone_code=self.family_phone_number_code, phone_number=phone)

    def get_office_phone_e164(self) -> str:
        phone = self.get_phone_without_zero(self.office_phone_number)
        return "+{phone_code}{phone_number}".format(phone_code=self.office_phone_number_code, phone_number=phone)

    def get_phone_without_zero(self, phone: str) -> str:
        if phone and phone[0] == '0':
            phone = phone[1:]
        return phone


class ExceptionMerge(TimeStampedModel):
    instruction = models.ForeignKey('instructions.Instruction', on_delete=models.CASCADE)
    file_detail = ArrayField(models.CharField(max_length=255, blank=True, null=True))

    def __str__(self):
        return ' '.join(['Exception in instructions : ', str(self.pk)])


class UnsupportedAttachment(models.Model):
    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE)
    file_content = models.BinaryField()
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)

    def __str__(self):
        return self.file_name.split('\\')[-1]
