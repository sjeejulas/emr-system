from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.utils import timezone
from common.functions import send_mail
from django.http import HttpRequest
from django_clamd.validators import validate_file_infection
from common.models import TimeStampedModel
from common.functions import get_url_page
from accounts.models import ClientUser, GeneralPracticeUser, Patient, MedidataUser, User, GENERAL_PRACTICE_USER
from organisations.models import OrganisationGeneralPractice
from accounts import models as account_models
from snomedct.models import SnomedConcept, CommonSnomedConcepts
from .model_choices import *
from django.conf import settings
from typing import Set, Dict, Tuple, Iterable
from payment.models import WeeklyInvoice
from payment.model_choices import FEE_TYPE_CHOICE

import datetime

PIPELINE_INSTRUCTION_LINK = get_url_page('instruction_pipeline')
TITLE_CHOICE = account_models.TITLE_CHOICE


class InstructionPatient(models.Model):
    patient_user = models.ForeignKey(Patient, related_name='instruction_patients', on_delete=models.CASCADE, blank=True, null=True)
    patient_title = models.CharField(max_length=3, choices=TITLE_CHOICE, verbose_name='Title*')
    patient_first_name = models.CharField(max_length=255, verbose_name="First name*")
    patient_last_name = models.CharField(max_length=255, verbose_name="Last name*")
    patient_dob = models.DateField(null=True)
    patient_dob_day = models.CharField(max_length=10, blank=True)
    patient_dob_month = models.CharField(max_length=10, blank=True)
    patient_dob_year = models.CharField(max_length=10, blank=True)
    patient_postcode = models.CharField(max_length=255, verbose_name='Postcode*')
    patient_address_number = models.CharField(max_length=255, blank=True)
    patient_address_line1 = models.CharField(max_length=255)
    patient_address_line2 = models.CharField(max_length=255, blank=True)
    patient_address_line3 = models.CharField(max_length=255, blank=True)
    patient_city = models.CharField(max_length=255)
    patient_county = models.CharField(max_length=255)
    patient_nhs_number = models.CharField(max_length=10, blank=True)
    patient_email = models.EmailField(max_length=255, blank=True)
    patient_telephone_code = models.CharField(max_length=10, blank=True)
    patient_telephone_mobile = models.CharField(max_length=255, blank=True)
    patient_alternate_code = models.CharField(max_length=10, blank=True)
    patient_alternate_phone = models.CharField(max_length=255, blank=True)
    patient_emis_number = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Instruction Patient Information"

    def __str__(self):
        return "{first_name} {last_name} {dob}".format(
            first_name=self.patient_first_name, last_name=self.patient_last_name, dob=self.patient_dob
        )

    def get_telephone_e164(self) -> str:
        phone = self.get_phone_without_zero(self.patient_telephone_mobile)
        return "+%s%s"%(self.patient_telephone_code, phone)

    def get_alternate_e164(self) -> str:
        phone = self.get_phone_without_zero(self.patient_alternate_phone)
        return "+%s%s"%(self.patient_alternate_code, phone)

    def get_phone_without_zero(self, phone: str) -> str:
        if phone and phone[0] == '0':
            phone = phone[1:]
        return phone

    def get_full_name(self) -> str:
        return ' '.join([self.get_patient_title_display(), self.patient_first_name, self.patient_last_name])


class Instruction(TimeStampedModel, models.Model):
    client_user = models.ForeignKey(ClientUser, on_delete=models.CASCADE, verbose_name='Client', null=True)
    gp_user = models.ForeignKey(GeneralPracticeUser, on_delete=models.CASCADE, verbose_name='GP Allocated', null=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, verbose_name='Patient')
    completed_signed_off_timestamp = models.DateTimeField(null=True, blank=True, verbose_name='Completed')
    rejected_timestamp = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    rejected_note = models.TextField(blank=True)
    rejected_reason = models.IntegerField(choices=INSTRUCTION_REJECT_TYPE, null=True, blank=True)
    type = models.CharField(max_length=4, choices=INSTRUCTION_TYPE_CHOICES)
    type_catagory = models.IntegerField(choices=FEE_TYPE_CHOICE, null=True)
    final_report_date = models.TextField(blank=True)
    gp_earns = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    medi_earns = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.IntegerField(choices=INSTRUCTION_STATUS_CHOICES, default=INSTRUCTION_STATUS_NEW)
    consent_form = models.FileField(upload_to='consent_forms', null=True, blank=True, validators=[validate_file_infection])
    patient_information = models.OneToOneField(InstructionPatient, on_delete=models.CASCADE, verbose_name='Patient')
    gp_title_from_client = models.CharField(max_length=5, choices=TITLE_CHOICE, blank=True)
    gp_initial_from_client = models.CharField(max_length=20, blank=True)
    gp_last_name_from_client = models.CharField(max_length=255, blank=True)

    date_range_from = models.DateField(null=True, blank=True)
    date_range_to = models.DateField(null=True, blank=True)

    gp_practice = models.ForeignKey(OrganisationGeneralPractice, on_delete=models.CASCADE)
    sars_consent = models.FileField(upload_to='consent_forms', null=True, blank=True)
    mdx_consent = models.FileField(upload_to='consent_forms', null=True, blank=True)

    # TODO Have to remove this field in the future because we already don't use file system anymore
    medical_report = models.FileField(upload_to='medical_reports', null=True, blank=True)
    medical_xml_report = models.FileField(upload_to='medical_xml_reports', null=True, blank=True)
    medical_with_attachment_report = models.FileField(upload_to='medical_with_attachment_reports', null=True, blank=True)
    download_attachments = models.TextField(blank=True)

    # File bytes content
    medical_report_byte = models.BinaryField()
    medical_with_attachment_report_byte = models.BinaryField()
    final_raw_medical_xml_report = models.TextField(blank=True)

    saved = models.BooleanField(default=False)
    deactivated = models.BooleanField(default=False, verbose_name="Deactivated at patient request")
    medi_ref = models.IntegerField(null=True, blank=True, verbose_name="Medi Ref.")
    your_ref = models.CharField(max_length=80, null=True, blank=True, verbose_name="Client Ref.")
    client_payment_reference = models.CharField(max_length=255, blank=True)
    gp_payment_reference = models.CharField(max_length=255, blank=True)
    fee_calculation_start_date = models.DateTimeField(null=True, blank=True)

    ins_max_day_lvl_1 = models.PositiveSmallIntegerField(default=3)
    ins_max_day_lvl_2 = models.PositiveSmallIntegerField(default=7)
    ins_max_day_lvl_3 = models.PositiveSmallIntegerField(default=11)
    ins_max_day_lvl_4 = models.PositiveSmallIntegerField(default=12)
    ins_amount_rate_lvl_1 = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    ins_amount_rate_lvl_2 = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    ins_amount_rate_lvl_3 = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    ins_amount_rate_lvl_4 = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)

    invoice_in_week = models.ForeignKey(WeeklyInvoice, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_pdf_file = models.FileField(upload_to='invoices', null=True, blank=True)

    # Patient Acceptance DateTime
    patient_acceptance = models.DateTimeField(null=True, blank=True, verbose_name='T&C Accpeted Date Time')

    # Notification when completed
    patient_notification = models.BooleanField(default=False)
    third_party_notification = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Instruction"
        ordering = ('-created',)
        permissions = (
            ('create_sars', 'Create SARS'),
            ('reject_amra', 'Reject AMRA'),
            ('reject_sars', 'Reject SARS'),
            ('process_amra', 'Process AMRA'),
            ('process_sars', 'Process SARS'),
            ('allocate_gp', 'Allocate to other user to process'),
            ('sign_off_amra', 'Sign off AMRA'),
            ('sign_off_sars', 'Sign off SARS'),
            ('view_completed_amra', 'View completed AMRA'),
            ('view_completed_sars', 'View completed SARS'),
            ('view_summary_report', 'View summary report'),
            ('view_account_pages', 'view account page'),
            ('authorise_fee', 'Authorise Fee'),
            ('amend_fee', 'Amend Fee'),
            ('authorise_bank_account', 'view Bank detail'),
            ('amend_bank_account', 'view/edit Bank detail')
        )

    def __str__(self):
        return 'Instruction #{pk}'.format(pk=self.pk)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.medi_ref:
            self.medi_ref = settings.MEDI_REF_NUMBER + self.pk
            self.save()

        if not self.fee_calculation_start_date:
            now = timezone.now()
            if now.strftime("%A") == "Friday" and now.hour > 12:
                self.fee_calculation_start_date = now + datetime.timedelta(days=2)
            else:
                self.fee_calculation_start_date = now
            self.save()

    def in_progress(self, context: Dict[str, str]) -> None:
        self.status = INSTRUCTION_STATUS_PROGRESS
        if not self.gp_user:
            self.gp_user = context.get('gp_user', None)
        self.save()

    def reject(self, request: HttpRequest, context: Dict[str, str]) -> None:
        user = request.user
        if user.type == GENERAL_PRACTICE_USER:
            self.gp_user = user.userprofilebase.generalpracticeuser
            send_mail_bool = True
        else:
            send_mail_bool = False

        self.rejected_timestamp = timezone.now()
        self.rejected_by = user
        self.rejected_reason = context.get('rejected_reason', None)
        self.rejected_note = context.get('rejected_note', '')
        self.status = INSTRUCTION_STATUS_REJECT

        if send_mail_bool:
            patient_email = context.get('reject_patient_email', '')
            if patient_email != '':
                self.send_reject_email_to_patient(patient_email)
            if self.client_user:
                self.send_reject_email([self.client_user.user.email])
            if self.gp_user and self.gp_user.role == GeneralPracticeUser.OTHER_PRACTICE:
                emails = [medi.user.email for medi in MedidataUser.objects.all()]
                self.send_reject_email(emails)
                
        self.save()

    def send_reject_email_to_patient(self, patient_email: str) -> None:
        send_mail(
            'Rejected Instruction',
            'Unfortunately your instruction could not be completed on this occasion. Please contact your GP Surgery for more information',
            'MediData',
            patient_email,
            fail_silently=True,
            auth_user=settings.EMAIL_HOST_USER,
            auth_password=settings.EMAIL_HOST_PASSWORD,
        )

    def send_reject_email(self, to_email: str) -> None:
        send_mail(
            'Rejected Instruction',
            'You have a rejected instruction. Click here {link}?status=4&type=allType to see it.'.format(link=PIPELINE_INSTRUCTION_LINK),
            'MediData',
            to_email,
            fail_silently=True,
            auth_user=settings.EMAIL_HOST_USER,
            auth_password=settings.EMAIL_HOST_PASSWORD,
        )

    def snomed_concepts_ids_and_readcodes(self) -> Tuple[Set[int], Set[int]]:
        snomed_concepts_ids = set()
        readcodes = set()
        for sct in self.selected_snomed_concepts():
            if CommonSnomedConcepts.objects.filter(snomed_concept_code=sct).exists():
                snomed_concepts_ids.update(
                    CommonSnomedConcepts.objects.filter(snomed_concept_code=sct).first().descendant_snomed_id
                )
                readcodes.update(
                    CommonSnomedConcepts.objects.filter(snomed_concept_code=sct).first().descendant_readcodes
                )
            else:
                snomed_descendants = sct.descendants(ret_descendants=set())
                snomed_concepts_ids.update(
                    map(lambda sc: sc.external_id, snomed_descendants)
                )

                readcodes.update(
                    map(lambda rc: rc.ext_read_code, sct.descendant_readcodes(snomed_descendants))
                )
        return snomed_concepts_ids, readcodes

    def readcodes(self) -> Set[str]:
        readcodes = set()
        for sct in self.selected_snomed_concepts():
            readcodes.update(
                map(lambda rc: rc.ext_read_code, sct.descendant_readcodes())
            )
        return readcodes

    def selected_snomed_concepts(self) -> Iterable[SnomedConcept]:
        return SnomedConcept.objects.filter(
            instructionconditionsofinterest__instruction=self.id
        )

    def get_inner_selected_snomed_concepts(self):
        snomed = set()
        for snomed_value in self.selected_snomed_concepts():
            snomed.add(snomed_value.fsn_description)
        return snomed

    def get_type(self):
        return self.type

    def is_sars(self) -> bool:
        return self.type == SARS_TYPE

    def is_amra(self) -> bool:
        return self.type == AMRA_TYPE

    def get_str_date_range(self) -> str:
        if self.date_range_from is None:
            return None
        str_date_range = str(self.date_range_from) + ' - ' + str(self.date_range_to)
        return str_date_range

    def get_client_org_name(self) -> str:
        return self.client_user.organisation.trading_name
        
    get_client_org_name.allow_tags = False
    get_client_org_name.short_description = 'Client organisation name'
    


class InstructionAdditionQuestion(models.Model):
    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE, related_name='addition_questions')
    question = models.CharField(max_length=255, blank=True)
    response_mandatory = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Instruction Addition Question"

    def __str__(self):
        return self.question


class InstructionAdditionAnswer(models.Model):
    question = models.OneToOneField(InstructionAdditionQuestion, on_delete=models.CASCADE)
    answer = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Instruction Addition Answer"

    def __str__(self):
        return self.answer


class InstructionConditionsOfInterest(models.Model):
    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE)
    snomedct = models.ForeignKey(SnomedConcept, on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "Instruction Conditions Of Interest"

    def __str__(self):
        return "{} ({})".format(self.snomedct.fsn_description, self.snomedct.external_id)


class Setting(models.Model):
    consent_form = models.FileField(upload_to='consent_forms', null=True, blank=True, validators=[validate_file_infection])

    def save(self, *args, **kwargs):
        self.__class__.objects.exclude(id=self.id).delete()
        super(Setting, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        try:
            return cls.objects.get()
        except cls.DoesNotExist:
            return cls()


class ClientNote(models.Model):
    note = models.CharField(max_length=255)

    def __str__(self):
        return self.note


class InstructionClientNote(models.Model):
    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE, related_name='client_notes')
    note = models.CharField(max_length=255)
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Instruction Client Note"
        ordering = ("-created_date",)

    def __str__(self):
        return self.note


class InstructionReminder(models.Model):
    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE, related_name='reminders')
    note = models.CharField(max_length=255)
    created_date = models.DateTimeField(auto_now_add=True)
    reminder_day = models.IntegerField()

    class Meta:
        verbose_name = "Instruction Reminder"

    def __str__(self):
        return self.note


class InstructionInternalNote(models.Model):
    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE, related_name='internal_notes')
    note = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Instruction Internal Note"

    def __str__(self):
        return self.note
