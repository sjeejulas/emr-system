from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from .emisapiservices import services
from .dummy_models import DummyPatient, DummyPractice, DummySnomedConcept
from snomedct.models import SnomedConcept
from .xml.patient_list import PatientList
from .xml.medical_record import MedicalRecord
from .xml.medical_report_decorator import MedicalReportDecorator
from .xml.base64_attachment import Base64Attachment
from .xml.xml_utils import redaction_elements
import datetime
# Create your views here.


# purpose of the view is to test the server class
# using dummy class for patient and practice model
def get_patient_list(request):
    patient = DummyPatient('patient_first_name', 'patient_last_name', datetime.datetime.strptime('1986-09-04', "%Y-%m-%d"))

    raw_xml = services.GetPatientList(patient).call()
    patients = PatientList(raw_xml).patients()

    return render(request, 'services/test.html', {
        'patients': patients,
        'xml_raw_data': raw_xml
    })


def get_patient_record(request):
    patient_number = '2820'
    raw_xml = services.GetMedicalRecord(patient_number).call()
    redacted = redaction_elements(raw_xml, [
        ".//Event[GUID='{12904CD5-1B75-4BBF-95ED-338EC0C6A5CC}']",
        ".//ConsultationElement[Attachment/GUID='{6BC4493F-DB5F-4C74-B585-05B0C3AA53C9}']",
        ".//ConsultationElement[Referral/GUID='{1FA96ED4-14F8-4322-B6F5-E00262AE124D}']",
        ".//Medication[GUID='{5A786379-97B4-44FD-9726-E3C9C5E34E32}']",
        ".//Medication[GUID='{A18F2B49-8ECA-436A-98F8-5C26E4F495DC}']",
        ".//Medication[GUID='{A1C57DC5-CCC6-4CD2-871B-C8A07ADC7D06}']",
        ".//Event[GUID='{EC323C66-8698-4802-9731-6AC229B11D6D}']",
        ".//Event[GUID='{6F058DA7-420E-422A-9CE6-84F3CA9CA246}']"
    ])
    medical_record = MedicalRecord(raw_xml)
    # medical_record = MedicalReportDecorator(raw_xml, None)

    return render(request, 'services/test.html', {
        'xml_raw_data': raw_xml,
        'medical_record': medical_record
    })


def get_patient_attachment(request) -> HttpResponse:
    patient_number = '2820'
    attachment_identifier = '{5C37D79F-8DB5-4754-BBDE-43BF6AFE19DE}'
    raw_xml = services.GetAttachment(patient_number, attachment_identifier).call()

    base64_attachment = Base64Attachment(raw_xml)

    response = HttpResponse(base64_attachment.data(), content_type='application/octet-stream')
    response['Content-Disposition'] = 'inline;filename={}'.format(base64_attachment.file_basename())
    response['Content-Transfer-Encoding'] = 'binary'
    return response


def handle_error(request, code):
    return render(request, 'errors/handle_errors_emis.html', {
        'code': code,
    })


def handler_403(request, reason=''):
    status_code = 403
    message = 'Permission Denied. Please try again later or contact the admin.'
    response = render(request, 'errors/handle_errors.html', {
        'code': status_code,
        'message': message,
        'reason': reason
    })
    response.status_code = status_code
    return response


def handler_404(request, exception=None, template_name='handle_errors.html'):
    status_code = 404
    message = 'Page not found. Please try again later or contact the admin.'
    response = render(request, 'errors/handle_errors.html', {
        'code': status_code,
        'message': message
    })
    response.status_code = status_code
    return response


def handler_500(request, template_name='handle_errors.html') -> HttpResponse:
    status_code = 500
    message = 'There is an error on this page. Please try again later or contact the admin.'
    response = render(request, 'errors/handle_errors.html', {
        'code': status_code,
        'message': message
    })
    response.status_code = status_code
    return response
