from common.functions import send_mail
from django.conf import settings
from django.shortcuts import reverse

from instructions.models import Instruction
from instructions.model_choices import INSTRUCTION_STATUS_PROGRESS
from medicalreport.models import AmendmentsForRecord, RedactedAttachment
from medicalreport.reports import generate_redact_pdf, tiff_processing
from services.emisapiservices import services
from services.xml.medical_report_decorator import MedicalReportDecorator
from services.xml.base64_attachment import Base64Attachment

from celery import shared_task
from PIL import Image

import io
import img2pdf
import subprocess
import uuid
import time
import logging
import reportlab
import reportlab.lib.pagesizes as pdf_sizes

EVENT_LOGGER = logging.getLogger('medidata.event')
TEMP_DIR = settings.BASE_DIR + '/static/generic_pdf/'


@shared_task(bind=True)
def prepare_medicalreport_data(self, instruction_id, notify_mail=True):
    """
        1. Keep XML to our DB.
        2. Prepare Relations third party data
        3. Redaction attachment and keep it with instruction
    :return:
    """
    try:
        instruction = Instruction.objects.get(id=instruction_id)
        time.sleep(5)
        amendments = AmendmentsForRecord.objects.filter(instruction=instruction).first()

        if not amendments:
            aes_key = uuid.uuid4().hex
            # create AmendmentsForRecord with aes_key first then save raw_xml and encrypted with self aes_key
            amendments = AmendmentsForRecord.objects.create(instruction=instruction, raw_medical_xml_aes_key=aes_key)

        raw_xml = services.GetMedicalRecord(amendments.patient_emis_number, gp_organisation=instruction.gp_practice).call()
        if isinstance(raw_xml, str):
            amendments.raw_medical_xml_encrypted = raw_xml
            amendments.save()
            medical_record_decorator = MedicalReportDecorator(raw_xml, instruction)
            for attachment in medical_record_decorator.attachments():
                pdf_path = ''
                pdf_byte = b''

                attachment_id = attachment.dds_identifier()
                raw_attachment_xml = services.GetAttachment(
                    instruction.patient_information.patient_emis_number,
                    attachment_id,
                    gp_organisation=instruction.gp_practice
                ).call()
                raw_attachment_byte = Base64Attachment(raw_attachment_xml).data()

                file_name = Base64Attachment(raw_attachment_xml).filename().split('\\')[-1]
                file_type = file_name.split('.')[-1]

                # for each type of attachment we want to set "pdf_path" or "pdf_byte"
                if file_type == 'pdf':
                    # set pdf_byte
                    pdf_byte = raw_attachment_byte

                elif file_type in ['doc', 'docx', 'rtf']:
                    # set pdf_path
                    buffer = io.BytesIO()
                    buffer.write(raw_attachment_byte)
                    tmp_file = '%s_tmp.%s' % (instruction.pk, file_type)
                    f = open(TEMP_DIR + tmp_file, 'wb')
                    f.write(buffer.getvalue())
                    f.close()
                    subprocess.call(
                        ("export HOME=/tmp && libreoffice --headless --convert-to pdf --outdir " + TEMP_DIR + " " + TEMP_DIR + "/" + tmp_file),
                        shell=True
                    )
                    pdf_path = TEMP_DIR + '%s_tmp.pdf' % instruction.pk

                elif file_type in ['jpg', 'jpeg', 'png', 'tiff', 'tif']:
                    # set pdf_byte
                    buffer = io.BytesIO(raw_attachment_byte)
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
                        pdf_byte = out_pdf_io.getvalue()
                    else:
                        image.save(TEMP_DIR + 'img_temp_%s.' % instruction.pk + image_format)
                        pdf_byte = img2pdf.convert(TEMP_DIR + 'img_temp_%s.' % instruction.pk + image_format)

                else:
                    # Unsupported file type
                    pass

                if pdf_path or pdf_byte:
                    # redacted attachment
                    redacted_count, pdf_page_buffer = generate_redact_pdf(
                        instruction.patient_information.patient_first_name,
                        instruction.patient_information.patient_last_name,
                        pdf_byte=pdf_byte,
                        pdf_path=pdf_path
                    )

                    # keep redacted attachment
                    RedactedAttachment.objects.create(
                        instruction=instruction,
                        name=file_name,
                        dds_identifier=attachment_id,
                        raw_attachment_file_content=pdf_page_buffer.getvalue(),
                        redacted_count=redacted_count
                    )
                else:
                    RedactedAttachment.objects.create(
                        instruction=instruction,
                        name=file_name,
                        dds_identifier=attachment_id,
                        raw_attachment_file_content=b'',
                    )
        else:
            EVENT_LOGGER.error('Unable to connect to EMIS for instruction No. (%s).' % instruction.id)

        # set IN_PROGRESS status and notify by email to gp
        instruction.status = INSTRUCTION_STATUS_PROGRESS
        instruction.save()
        if notify_mail:
            body_message_1 = 'The redaction process is now complete for instruction {medi_ref}.'.format(
                medi_ref=instruction.medi_ref
            )
            body_message_2 = ' Click here {link} to complete the report.'.format(
                                link=settings.EMR_URL + reverse('instructions:view_pipeline')
                            )
            body_message = body_message_1 + body_message_2
            send_mail(
                'Redaction Process now Complete {medi_ref}'.format(medi_ref=instruction.medi_ref),
                body_message,
                'MediData',
                [instruction.gp_user.user.email, instruction.gp_practice.organisation_email],
                fail_silently=False
            )
    except Exception as e:
        EVENT_LOGGER.error('Preparing asynchronous medical report data hit and unexpected err (%s).' % repr(e))

