from django.conf import settings
import urllib
import requests
import logging
from django.utils import timezone
from organisations.models import OrganisationGeneralPractice
from accounts.models import Patient
from requests import HTTPError
import time


logger = logging.getLogger('timestamp')
event_logger = logging.getLogger('medidata.event')


class EmisAPIServiceBase:
    def __init__(self, gp_organisation):
        self.emis_username = gp_organisation.operating_system_username
        self.emis_password = gp_organisation.operating_system_salt_and_encrypted_password
        self.emis_organisation_code = gp_organisation.operating_system_organisation_code

    def uri(self) -> str:
        raise NotImplementedError(
            "Inheriting classes must implement this method."
        )

    def call(self) -> str:
        request_uri = self.uri()
        start_time = timezone.now()
        for i in range(9):
            r = requests.get(
                request_uri,
                auth=(
                    self.emis_username,
                    self.emis_password,
                )
            )
            if r.status_code == 200:
                break
            else:
                time.sleep(0.2)
        end_time = timezone.now()
        total_time = end_time - start_time
        if 'attachments' not in request_uri:
            logger.info("[CALL EMIS] %s seconds with url %s"%(total_time.seconds, request_uri))

        http_error_msg = ''
        if isinstance(r.reason, bytes):
            try:
                reason = r.reason.decode('utf-8')
            except UnicodeDecodeError:
                reason = r.reason.decode('iso-8859-1')
        else:
            reason = r.reason

        if 400 <= r.status_code < 500:
            http_error_msg = u'%s Client Error: %s for url: %s \n' \
                             u'Message: %s' % (r.status_code, reason, r.url, r.text)

        elif 500 <= r.status_code < 600:
            http_error_msg = u'%s Server Error: %s for url: %s \n' \
                             u'Message: %s' % (r.status_code, reason, r.url, r.text)

        if http_error_msg:
            event_logger.error('FAILED: calling EMIS, reason:{http_error_msg}'.format(http_error_msg=http_error_msg))
            return r.status_code
        return r.text


class GetAttachment(EmisAPIServiceBase):
    def __init__(self, patient_number: str, attachment_identifier: str, gp_organisation: OrganisationGeneralPractice):
        super().__init__(gp_organisation)
        self.patient_number = patient_number
        self.attachment_identifier = attachment_identifier

    def uri(self) -> str:
        uri = "{host}/api/organisations/{organisation_id}/patients/{patient_number}/attachments/{attachment_identifier}".format(
            host=settings.EMIS_API_HOST,
            organisation_id=self.emis_organisation_code,
            patient_number=self.patient_number,
            attachment_identifier=urllib.parse.quote(self.attachment_identifier, safe=''))
        return uri


class GetPatientList(EmisAPIServiceBase):
    def __init__(self, patient: Patient, gp_organisation: OrganisationGeneralPractice):
        super().__init__(gp_organisation)
        self.patient = patient

    def search_term(self) -> str:
        terms = [
            self.patient.patient_first_name,
            self.patient.patient_last_name,
        ]
        if self.patient.patient_dob is not None:
            terms.append(self.patient.patient_dob.strftime("%d/%m/%Y"))
        terms = " ".join([term for term in terms if term])
        return urllib.parse.quote(terms, safe='')

    def uri(self):
        uri = "{host}/api/organisations/{organisation_id}/patients?q={search_term}".format(
            host=settings.EMIS_API_HOST,
            organisation_id=self.emis_organisation_code,
            search_term=self.search_term())
        return uri


class GetMedicalRecord(EmisAPIServiceBase):
    def __init__(self, patient_number: str,  gp_organisation: OrganisationGeneralPractice):
        super().__init__(gp_organisation)
        self.patient_number = patient_number

    def uri(self) -> str:
        uri = "{host}/api/organisations/{organisation_id}/patients/{patient_number}/medical_record".format(
            host=settings.EMIS_API_HOST,
            organisation_id=self.emis_organisation_code,
            patient_number=self.patient_number)
        return uri


class GetEmisStatusCode(EmisAPIServiceBase):
    def uri(self) -> str:
        uri = "{host}/api/organisations/{organisation_id}/patients?q=medidataemislogintest".format(
            host=settings.EMIS_API_HOST,
            organisation_id=self.emis_organisation_code
        )
        return uri

    def call(self) -> int:
        request_uri = self.uri()
        r = requests.get(
            request_uri,
            auth=(
                self.emis_username,
                self.emis_password,
            )
        )
        event_logger.info('EMIS Polling Status {result}'.format(result='SUCCESS' if r.status_code == 200 else 'UNAUTHORIZED'))
        return r.status_code
