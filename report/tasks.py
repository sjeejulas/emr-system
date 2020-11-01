from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from django.template import loader
from common.functions import send_mail
from django.template.loader import get_template

from services.xml.base64_attachment import Base64Attachment
from medicalreport.models import AmendmentsForRecord, ReferencePhrases, RedactedAttachment
from library.models import LibraryHistory
from services.xml.medical_report_decorator import MedicalReportDecorator
from services.emisapiservices import services
from services.xml.xml_utils import xml_parse, lxml_to_string
from instructions.models import Instruction
from instructions.model_choices import INSTRUCTION_STATUS_COMPLETE, INSTRUCTION_STATUS_RERUN
from report.mobile import SendSMS
from report.views import send_third_party_message
from report.models import ExceptionMerge, UnsupportedAttachment, ThirdPartyAuthorisation
import xhtml2pdf.pisa as pisa
from medicalreport.templatetags.custom_filters import format_date_filter
from medicalreport.reports import generate_redact_pdf
from services.xml.medication import Medication

# from silk.profiling.profiler import silk_profile

from celery import shared_task
from PIL import Image
import PyPDF2
import subprocess
import img2pdf
import reportlab
import reportlab.lib.pagesizes as pdf_sizes
import logging
import io
import uuid
import glob
import os
import requests

logger = logging.getLogger(__name__)
time_logger = logging.getLogger('timestamp')
event_logger = logging.getLogger('medidata.event')
email_logger = logging.getLogger('email.error')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = BASE_DIR + '/medicalreport/templates/medicalreport/reports/unsupport_files.html'


def send_patient_mail(scheme: str, host: str,  unique_url: str, instruction: Instruction) -> None:
    report_link = scheme + '://' + host + '/report/' + str(instruction.pk) + '/patient/' + unique_url
    send_mail(
        'Notification from your GP surgery',
        '',
        'MediData',
        [instruction.patient_information.patient_email],
        fail_silently=False,
        html_message=loader.render_to_string('medicalreport/patient_email.html', {
            'surgery_name': instruction.gp_practice,
            'report_link': report_link
        })
    )


def link_callback(uri: str, rel) -> str:
    sUrl = settings.STATIC_URL
    sRoot = settings.STATIC_ROOT

    if uri.startswith(sUrl):
        path = os.path.join(sRoot, uri.replace(sUrl, ""))
    else:
        path = sRoot

    if sRoot == 'static':
        path = BASE_DIR + '/medi/' + path

    if not os.path.isfile(path):
        raise Exception('static URI must start with %s' % (sUrl))
    return path


@shared_task(bind=True)
def generate_medicalreport_with_attachment(self, instruction_info: dict, report_link_info: dict):
    start_time = timezone.now()

    try:
        instruction_id = instruction_info['id']
        instruction = get_object_or_404(Instruction, id=instruction_id)
        redaction = get_object_or_404(AmendmentsForRecord, instruction=instruction_id)

        # redaction final raw xml
        from medicalreport.functions import redact_name_relations_third_parties
        relations = [relation.name for relation in ReferencePhrases.objects.all()]
        parsed_xml = xml_parse(instruction.final_raw_medical_xml_report)
        redaction_xml_tag = ['Description', 'DescriptiveText'] + Medication.DESCRIPTION_XPATHS
        # third parties redaction and replace all word toolbox history
        for i in parsed_xml.iter():
            if i.text and (i.tag in redaction_xml_tag):
                i.text = redact_name_relations_third_parties(i.text, relations, list(LibraryHistory.objects.filter(instruction=instruction, action=LibraryHistory.ACTION_REPLACE_ALL).values_list('new', flat=True)))

        # library toolbox redaction history
        for history in LibraryHistory.objects.filter(instruction=instruction, action__in=[LibraryHistory.ACTION_REPLACE, LibraryHistory.ACTION_REPLACE_ALL, LibraryHistory.ACTION_HIGHLIGHT_REDACT]):
            replace = '' if history.action is LibraryHistory.ACTION_HIGHLIGHT_REDACT else history.new
            if history.section in ['acute_medications', 'repeat_medications']:
                for medication_desc_xapth in Medication.DESCRIPTION_XPATHS:
                    description_element = parsed_xml.find(history.xpath + medication_desc_xapth)
                    if description_element is not None:
                        description_element.text = description_element.text.replace(history.old, replace)
            elif history.section in ['significant_active', 'significant_past']:
                for problem_desc_xpath in ['DisplayTerm', 'Code/Term']:
                    description_element = parsed_xml.find(history.xpath + problem_desc_xpath)
                    if description_element is not None:
                        description_element.text = description_element.text.replace(history.old, replace)
            elif history.section == 'consultations':
                for consultation_desc_xpath in ['DisplayTerm', 'TermID/Term', 'ReferralReason', 'DescriptiveText', 'Code/Term'] + Medication.DESCRIPTION_XPATHS:
                    description_element = parsed_xml.find(history.xpath + consultation_desc_xpath)
                    if description_element is not None:
                        description_element.text = description_element.text.replace(history.old, replace)
            elif history.section == 'referrals':
                for referral_desc_xpath in ['DisplayTerm', 'ReferralReason', 'DescriptiveText', 'Code/Term', 'TermID/Term']:
                    description_element = parsed_xml.find(history.xpath + referral_desc_xpath)
                    if description_element is not None:
                        description_element.text = description_element.text.replace(history.old, replace)
            elif history.section == 'allergies':
                for allergy_desc_xpath in ['DisplayTerm', 'Code/Term', 'DescriptiveText']:
                    description_element = parsed_xml(history.xpath + allergy_desc_xpath)
                    if description_element is not None:
                        description_element.text = description_element.text.replace(history.old, replace)


        str_xml = lxml_to_string(parsed_xml)
        instruction.final_raw_medical_xml_report = str_xml.decode('utf-8')

        medical_record_decorator = MedicalReportDecorator(instruction.final_raw_medical_xml_report, instruction)
        output = PyPDF2.PdfFileWriter()

        final_report_buffer = io.BytesIO(instruction.medical_report_byte)
        medical_report = PyPDF2.PdfFileReader(final_report_buffer)

        # append uploaded consent pdf file to output file if it exists..
        if instruction.mdx_consent:
            consent_file = PyPDF2.PdfFileReader(instruction.mdx_consent)

            for page_num in range(consent_file.getNumPages()):
                output.addPage(consent_file.getPage(page_num))

        # add each page of medical report to output file
        for page_num in range(medical_report.getNumPages()):
            output.addPage(medical_report.getPage(page_num))

        # create list of PdfFileReader obj from raw bytes of xml data
        attachments_pdf = []
        unique_file_name = []
        download_attachments = []
        exception_detail = list()
        folder = settings.BASE_DIR + '/static/generic_pdf/'
        for attachment in medical_record_decorator.attachments():
            try:
                unique = uuid.uuid4().hex
                unique_file_name.append(unique)
                xpaths = attachment.xpaths()
                description = attachment.description()
                date = format_date_filter(attachment.parsed_date())
                attachment_id = attachment.dds_identifier()
                if redaction.redacted(xpaths) is not True:
                    raw_xml_or_status_code = services.GetAttachment(
                        instruction.patient_information.patient_emis_number,
                        attachment_id,
                        gp_organisation=instruction.gp_practice).call()

                    file_name = Base64Attachment(raw_xml_or_status_code).filename()
                    file_type = file_name.split('.')[-1]
                    raw_attachment = Base64Attachment(raw_xml_or_status_code).data()
                    buffer = io.BytesIO(raw_attachment)
                    path_patient = instruction.patient_information.__str__()
                    save_path = settings.MEDIA_ROOT + '/patient_attachments/' + path_patient + '/'
                    if not os.path.exists(os.path.dirname(save_path)):
                        os.makedirs(os.path.dirname(save_path))

                    if file_type == 'pdf':
                        if settings.IMAGE_REDACTION_ENABLED:
                            redacted_count, redacted_pdf = generate_redact_pdf(
                                instruction.patient_information.patient_first_name,
                                instruction.patient_information.patient_last_name,
                                pdf_byte=raw_attachment
                            )

                            attachments_pdf.append(PyPDF2.PdfFileReader(redacted_pdf))
                        else:
                            attachments_pdf.append(PyPDF2.PdfFileReader(buffer))
                    elif file_type in ['doc', 'docx', 'rtf']:
                        tmp_file = 'temp_%s.' % unique + file_type
                        f = open(folder + tmp_file, 'wb')
                        f.write(buffer.getvalue())
                        f.close()
                        subprocess.call(
                            ("export HOME=/tmp && libreoffice --headless --convert-to pdf --outdir " + folder + " " + folder + "/" + tmp_file),
                            shell=True
                        )
                        if settings.IMAGE_REDACTION_ENABLED:
                            pdf_path = folder + 'temp_%s.pdf' % unique
                            redacted_count, redacted_pdf = generate_redact_pdf(
                                instruction.patient_information.patient_first_name,
                                instruction.patient_information.patient_last_name,
                                pdf_path=pdf_path
                            )
                            attachments_pdf.append(PyPDF2.PdfFileReader(redacted_pdf))
                        else:
                            pdf = open(folder + 'temp_%s.pdf' % unique, 'rb')
                            attachments_pdf.append(PyPDF2.PdfFileReader(pdf))
                    elif file_type in ['jpg', 'jpeg', 'png', 'tiff', 'tif']:
                        image = Image.open(buffer)
                        image_format = image.format
                        if image_format == "TIFF":
                            max_pages = 200
                            height = image.tag[0x101][0]
                            width = image.tag[0x100][0]
                            out_pdf_io = io.BytesIO()
                            c = reportlab.pdfgen.canvas.Canvas(out_pdf_io, pagesize=pdf_sizes.letter)
                            pdf_width, pdf_height = pdf_sizes.letter
                            page = 0
                            while True:
                                try:
                                    image.seek(page)
                                except EOFError:
                                    break
                                if pdf_width * height / width <= pdf_height:
                                    c.drawInlineImage(image, 0, 0, pdf_width, pdf_width * height / width)
                                else:
                                    c.drawInlineImage(image, 0, 0, pdf_height * width / height, pdf_height)
                                c.showPage()
                                if max_pages and page > max_pages:
                                    break
                                page += 1
                            c.save()

                            if settings.IMAGE_REDACTION_ENABLED:
                                redacted_count, redacted_pdf = generate_redact_pdf(
                                    instruction.patient_information.patient_first_name,
                                    instruction.patient_information.patient_last_name,
                                    pdf_byte=out_pdf_io.getvalue()
                                )

                                attachments_pdf.append(PyPDF2.PdfFileReader(redacted_pdf))
                            else:
                                attachments_pdf.append(PyPDF2.PdfFileReader(out_pdf_io))
                        else:
                            image.save(folder + 'img_temp_%s.' % unique + image_format)
                            pdf_bytes = img2pdf.convert(folder + 'img_temp_%s.' % unique + image_format)

                            if settings.IMAGE_REDACTION_ENABLED:
                                redacted_count, redacted_pdf = generate_redact_pdf(
                                    instruction.patient_information.patient_first_name,
                                    instruction.patient_information.patient_last_name,
                                    pdf_byte=pdf_bytes
                                )
                                attachments_pdf.append(PyPDF2.PdfFileReader(redacted_pdf))
                            else:
                                buffer = io.BytesIO(pdf_bytes)
                                attachments_pdf.append(PyPDF2.PdfFileReader(buffer))
                    else:
                        # zipped unsupported file type
                        file_name = Base64Attachment(raw_xml_or_status_code).filename()
                        buffer = io.BytesIO()
                        buffer.write(raw_attachment)
                        save_file = file_name.split('\\')[-1]
                        f = open(save_path + save_file, 'wb')
                        f.write(buffer.getvalue())
                        f.close()
                        download_attachments.append(save_file)

                        # keep unsupported file type
                        UnsupportedAttachment.objects.get_or_create(
                            instruction=instruction,
                            file_name=file_name,
                            file_content=buffer.getvalue(),
                            defaults={
                                'file_type': file_type,
                            },

                        )

            except Exception as e:
                exception_detail.append(date + ' ' + description)
                logger.error(e)

        if download_attachments:
            template = get_template(REPORT_DIR)
            html = template.render({'attachments': download_attachments})
            pdf_file = io.BytesIO()
            pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), pdf_file, link_callback=link_callback)
            if not pdf.err:
                attachments_pdf.append(PyPDF2.PdfFileReader(pdf_file))

        # add each page of each attachment to output file
        for pdf in attachments_pdf:
            if pdf.isEncrypted:
                pdf.decrypt(password='')
            for page_num in range(pdf.getNumPages()):
                output.addPage(pdf.getPage(page_num))

        pdf_page_buf = io.BytesIO()
        output.write(pdf_page_buf)

        uuid_hex = uuid.uuid4().hex
        instruction.medical_with_attachment_report_byte = pdf_page_buf.getvalue()
        instruction.medical_with_attachment_report.save('report_with_attachments_%s.pdf' % uuid_hex,
                                                        ContentFile(pdf_page_buf.getvalue()))
        instruction.save()

        # remove temp files
        for unique in unique_file_name:
            for file_path in glob.glob(folder+'*{unique}*'.format(unique=unique)):
                os.remove(file_path)

    except Exception as e:
        # waiting for 5 min to retry
        exception_merge, created = ExceptionMerge.objects.update_or_create(
            instruction_id=instruction_id,
            defaults={'file_detail': "Instruction can't converting to PDF"},
        )
        instruction.status = INSTRUCTION_STATUS_RERUN
        instruction.save()
        raise self.retry(countdown=60*5, exc=e, max_retires=2)

    if exception_detail:
        exception_merge, created = ExceptionMerge.objects.update_or_create(
            instruction_id=instruction_id,
            defaults={'file_detail': exception_detail},
        )
        instruction.status = INSTRUCTION_STATUS_RERUN
        instruction.save()
    else:
        msg_line_1 = "Your GP surgery has completed your SAR request. We have sent you an email to access a copy."
        msg_line_2 = "This may have landed in your 'Junk mail'. Move to your inbox to activate the link."
        msg = "%s %s"%(msg_line_1, msg_line_2)

        third_party_info = ThirdPartyAuthorisation.objects.filter(patient_report_auth__url=report_link_info['unique_url']).first()
        SendSMS(number=instruction.patient_information.get_telephone_e164()).send(msg)

        if instruction.patient_notification:
            send_patient_mail(
                report_link_info['scheme'],
                report_link_info['host'],
                report_link_info['unique_url'],
                instruction
            )

        if instruction.third_party_notification:
            if third_party_info and third_party_info.email and third_party_info.office_phone_number:
                send_third_party_message(
                    third_party_info,
                    report_link_info['scheme'],
                    report_link_info['host'],
                    third_party_info.patient_report_auth)

        from medicalreport.functions import send_surgery_email
        send_surgery_email(instruction)

        instruction.download_attachments = ",".join(download_attachments)
        instruction.status = INSTRUCTION_STATUS_COMPLETE
        instruction.save()

    end_time = timezone.now()
    total_time = end_time - start_time
    time_logger.info(
        "[PROCESS ATTACHMENTS] %s seconds with patient %s" % (
            total_time.seconds, instruction.patient_information.__str__()
        )
    )
