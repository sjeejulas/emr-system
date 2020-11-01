from django.test import TestCase
from django.test import tag
from django.utils import timezone

from model_mommy import mommy

from instructions.models import (
    Instruction, InstructionAdditionQuestion, InstructionConditionsOfInterest,
    InstructionPatient
)
import datetime
from accounts.models import User, ClientUser, Patient, GeneralPracticeUser
from snomedct.models import SnomedConcept
from instructions.model_choices import *
from instructions.cron.notification_mail import instruction_notification_email_job
from organisations.models import OrganisationGeneralPractice
from django.core import mail
from django.contrib.contenttypes.models import ContentType
from snomedct.models import SnomedConcept


class InstructionReminderTest(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.gp_practice = mommy.make(OrganisationGeneralPractice, name='Test GP Practice', practcode='TEST0001')
        self.instruction = mommy.make(
            Instruction, gp_practice=self.gp_practice,
            type=SARS_TYPE
        )

    def test_reminder_3_days(self):
        self.instruction.created=self.now-datetime.timedelta(days=3)
        self.instruction.save()
        instruction_notification_email_job()
        self.assertEqual(3, self.instruction.reminders.filter(reminder_day=3).first().reminder_day)

    def test_reminder_7_days(self):
        self.instruction.created=self.now-datetime.timedelta(days=7)
        self.instruction.save()
        instruction_notification_email_job()
        self.assertEqual(7, self.instruction.reminders.filter(reminder_day=7).first().reminder_day)

    def test_reminder_14_days(self):
        self.instruction.created=self.now-datetime.timedelta(days=14)
        self.instruction.save()
        instruction_notification_email_job()
        self.assertEqual(14, self.instruction.reminders.filter(reminder_day=14).first().reminder_day)

    def test_reminder_21_days(self):
        self.instruction.created=self.now-datetime.timedelta(days=21)
        self.instruction.save()
        instruction_notification_email_job()
        self.assertEqual(21, self.instruction.reminders.filter(reminder_day=21).first().reminder_day)

    def test_reminder_30_days(self):
        self.instruction.created=self.now-datetime.timedelta(days=30)
        self.instruction.save()
        instruction_notification_email_job()
        self.assertEqual(30, self.instruction.reminders.filter(reminder_day=30).first().reminder_day)

class InstructionPatientTest(TestCase):
    def setUp(self):
        self.patient_telephone_code='111'
        self.patient_alternate_code='112'
        self.instruction_patient = mommy.make(InstructionPatient,
            patient_first_name='aaa',
            patient_last_name='bbb'
        )

    def test_get_phone_without_zero(self):
        self.assertEqual(InstructionPatient.get_phone_without_zero(self, '12345'), '12345')
        self.assertEqual(InstructionPatient.get_phone_without_zero(self, '012345'), '12345')

    def test_get_telephone_e164(self):
        telephone = InstructionPatient.get_phone_without_zero(self, '012345')
        self.assertEqual('+11112345', "+%s%s"%(self.patient_telephone_code, telephone))

    def test_get_alternate_e164(self):
        alternate = InstructionPatient.get_phone_without_zero(self, '054321')
        self.assertEqual('+11254321', "+%s%s"%(self.patient_alternate_code, alternate))


class InstructionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.to_email = 'sample@domain.com'
        cls.user_1 = mommy.make(User, username='test_user_1', first_name='client')
        cls.user_2 = mommy.make(User, username='test_user_2', first_name='patient')
        cls.user_3 = mommy.make(User, username='gpuser', first_name='gpuser')
        cls.client_user = mommy.make(ClientUser, user=cls.user_1)
        cls.patient = mommy.make(Patient, user=cls.user_2)
        cls.instruction = mommy.make(
            Instruction, client_user=cls.client_user, patient=cls.patient, type=SARS_TYPE
        )
        cls.sars = SARS_TYPE
        cls.amra = AMRA_TYPE

    def test_string_representation(self):
        instruction_string = str(self.instruction)
        instruction_id = self.instruction.id
        self.assertEqual(instruction_string, 'Instruction #{id}'.format(id=instruction_id))

    def test_in_progress(self):
        self.instruction.status = INSTRUCTION_STATUS_PROGRESS
        self.assertEqual(1, self.instruction.status)

    def test_reject(self):
        gpuser = mommy.make(
            GeneralPracticeUser,
            user=self.user_3,
            role=0
        )
        self.instruction.rejected_reason = "rejected reason"
        self.instruction.rejected_note = "rejected note"
        self.instruction.rejected_by = self.user_3
        self.instruction.rejected_timestamp = timezone.now()
        self.instruction.status = INSTRUCTION_STATUS_REJECT
        self.assertEqual(3, self.instruction.status)

    def test_send_no_reject_email_to_patient_or_client(self):
        self.assertEqual(len(mail.outbox), 0)

    def test_get_type(self):
        self.assertEqual('SARS', self.instruction.type)

    def test_is_sars(self):
        self.assertEqual('SARS', self.sars)

    def test_is_amra(self):
        self.assertEqual('AMRA', self.amra)


class InstructionAdditionQuestionTest(TestCase):
    def test_string_representation(self):
        instruction_addition_question = mommy.make(
            InstructionAdditionQuestion, question='test_question?'
        )
        self.assertEqual(str(instruction_addition_question), 'test_question?')


class InstructionConditionsOfInterestTest(TestCase):
    def test_string_representation(self):
        snomedct = mommy.make(
            SnomedConcept, fsn_description='fsn_description',
            external_id=1234567890
        )
        instruction_conditions_of_interest = mommy.make(
            InstructionConditionsOfInterest, snomedct=snomedct
        )
        self.assertEqual(
            str(instruction_conditions_of_interest),
            'fsn_description (1234567890)'
        )
