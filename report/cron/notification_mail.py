from common.functions import send_mail
from django.utils import timezone

from report.models import ThirdPartyAuthorisation

from smtplib import SMTPException
import logging

from django.conf import settings

event_logger = logging.getLogger('medidata.event')


def report_notification_expired_authorisation_job():
    current_date = timezone.now().date()
    third_party_authorisations = ThirdPartyAuthorisation.objects.all()
    for authorisation in third_party_authorisations:
        if authorisation.expired_date and current_date > authorisation.expired_date and not authorisation.expired:
            authorisation.expired = True
            authorisation.save()
            try:
                send_mail(
                    'Medical Report Authorisation Expired',
                    'Your access to the SAR report for {ref_number} has expired. Please contact your client if a third party access extension is required.'.format(
                        ref_number=authorisation.patient_report_auth.instruction.medi_ref,
                    ),
                    'MediData',
                    [authorisation.email],
                    fail_silently=True,
                    auth_user=settings.EMAIL_HOST_USER,
                    auth_password=settings.EMAIL_HOST_PASSWORD,
                )
            except SMTPException:
                event_logger.error('Notification mail expired')
