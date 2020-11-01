from common.functions import send_mail
from django.utils import timezone
from django.shortcuts import reverse
from django.db.models import Q
from instructions.models import Instruction, InstructionReminder
from instructions.model_choices import *
from django.template import loader
from accounts.models import User, PracticePreferences, GeneralPracticeUser
from common.functions import get_url_page
from datetime import timedelta

from smtplib import SMTPException
import logging

from django.conf import settings

logger = logging.getLogger('timestamp')
event_logger = logging.getLogger('medidata.event')


def instruction_notification_email_job():
    instruction_notification_sars()
    instruction_notification_amra()


def instruction_notification_amra():
    pending_instructions = Instruction.objects.filter(type='AMRA')
    pending_instructions = pending_instructions.filter(~Q(status__in=[INSTRUCTION_STATUS_COMPLETE, INSTRUCTION_STATUS_REJECT, INSTRUCTION_STATUS_PAID]))

    for instruction in pending_instructions:
        time_check = timezone.now() - instruction.fee_calculation_start_date
        if time_check.days == REJECT_PENDING_INSTRUCTION_DAY:
            auto_reject_amra_after_23days(instruction)
        elif (time_check.days == instruction.ins_max_day_lvl_1) or\
            (time_check.days == instruction.ins_max_day_lvl_2) or\
            (time_check.days == instruction.ins_max_day_lvl_3) or\
            (time_check.days == instruction.ins_max_day_lvl_4):
            send_email_amra(instruction)


def send_email_amra(instruction):
    subject_email = 'AMRA instruction not processed'

    # Send Email for GP.
    gp_email = set()
    instruction_link = settings.EMR_URL + reverse('instructions:view_reject', kwargs={'instruction_id': instruction.id})
    gp_managers = User.objects.filter(
            userprofilebase__generalpracticeuser__organisation=instruction.gp_practice.pk,
            userprofilebase__generalpracticeuser__role=GeneralPracticeUser.PRACTICE_MANAGER
        ).values('email')
    for email in gp_managers:
        gp_email.add(email['email'])

    if instruction.gp_user:
        gp_email.add(instruction.gp_user.user.email)

    try:
        send_mail(
            subject_email,
            'Outstanding Instruction- Optimise your fees!',
            'MediData',
            list(gp_email),
            fail_silently=True,
            html_message=loader.render_to_string('instructions/amra_chasing_email.html', {
                'link': instruction_link
            })
        )
    except SMTPException:
        event_logger.info('"AMRA" Send mail to GP FAILED')


def auto_reject_amra_after_23days(instruction):
    email_user = 'auto_system@medidata.co'
    auto_reject_user, created = User.objects.get_or_create(
        email=email_user,
        username=email_user,
        first_name='auto-reject'
    )

    instruction.status = INSTRUCTION_STATUS_REJECT
    instruction.rejected_reason = LONG_TIMES
    instruction.rejected_by = auto_reject_user
    instruction.rejected_timestamp = timezone.now()
    instruction.rejected_note = 'Instruction not process until dute date'
    instruction.save()

    instruction_link = settings.MDX_URL + reverse('instructions:view_reject', kwargs={'instruction_id': instruction.id})
    instruction_med_ref = instruction.medi_ref
    subject_reject_email = 'AMRA instruction was not processed'

    # Send Email for client.
    client_email = [instruction.client_user.user.email]
    try:
        send_mail(
            subject_reject_email,
            'Your instruction has been reject',
            'MediData',
            client_email,
            fail_silently=True,
            html_message=loader.render_to_string('instructions/amra_reject_email.html', {
                'med_ref': instruction_med_ref,
                'link': instruction_link
            })
        )
    except SMTPException:
        event_logger.info('"AMRA" Send mail to client FAILED')


def instruction_notification_sars():
    now = timezone.now()
    new_or_pending_instructions = Instruction.objects.filter(
        status__in=(INSTRUCTION_STATUS_NEW, INSTRUCTION_STATUS_PROGRESS),
        type=SARS_TYPE
    )

    date_period_admin = [3, 7, 14]
    date_period_surgery = [7, 14, 21, 30]
    for instruction in new_or_pending_instructions:
        diff_date = now - instruction.created
        if diff_date.days in date_period_admin or diff_date.days in date_period_surgery:
            gp_managers = User.objects.filter(
                userprofilebase__generalpracticeuser__organisation=instruction.gp_practice.pk,
                userprofilebase__generalpracticeuser__role=GeneralPracticeUser.PRACTICE_MANAGER
            ).values('email')
            try:
                if gp_managers and diff_date.days in date_period_admin:
                    send_mail(
                        'Outstanding  Instruction',
                        'You have an outstanding instruction. Click here {link} to see it.'.format(
                            link=settings.EMR_URL + reverse('instructions:view_pipeline')
                        ),
                        'MediData',
                        [gp['email'] for gp in gp_managers],
                        fail_silently=True,
                        auth_user=settings.EMAIL_HOST_USER,
                        auth_password=settings.EMAIL_HOST_PASSWORD,
                    )
                if instruction.gp_practice and instruction.gp_practice.organisation_email and diff_date.days in date_period_surgery:
                    send_mail(
                        'Outstanding  Instruction',
                        'You have an outstanding instruction. Click here {link} to see it.'.format(
                            link=settings.EMR_URL + reverse('instructions:view_pipeline')
                        ),
                        'MediData',
                        [instruction.gp_practice.organisation_email],
                        fail_silently=True,
                        auth_user=settings.EMAIL_HOST_USER,
                        auth_password=settings.EMAIL_HOST_PASSWORD,
                    )
                InstructionReminder.objects.create(
                    instruction_id=instruction.id,
                    note="note added to instruction for %s day reminder"%diff_date.days,
                    reminder_day=diff_date.days
                )
            except SMTPException:
                logging.error('Send mail FAILED to send message')


def send_email_to_practice_job():
    unstarted_instructions = Instruction.objects.filter(status=INSTRUCTION_STATUS_NEW)
    for instruction in unstarted_instructions:
        gp_practice = instruction.gp_practice
        practice_preferences = PracticePreferences.objects.get(gp_organisation=gp_practice)
        if practice_preferences.notification == 'DIGEST':
            send_mail(
                'New Instruction',
                'You have a New Instruction(s). Click here {link} to view'.format(link=settings.EMR_URL + reverse('instructions:view_pipeline')),
                'MediData',
                [gp_practice.organisation_email],
                fail_silently=True,
                auth_user=settings.EMAIL_HOST_USER,
                auth_password=settings.EMAIL_HOST_PASSWORD,
            )
