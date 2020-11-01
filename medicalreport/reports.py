import os
import logging
import re
import xhtml2pdf.pisa as pisa
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils import timezone
from django.shortcuts import render_to_response, render
from django.http import HttpResponse
from django.template.loader import get_template
from services.xml.base64_attachment import Base64Attachment
from services.emisapiservices import services
import reportlab
from django.urls import reverse
import reportlab.lib.pagesizes as pdf_sizes
from PIL import Image
from django.conf import settings
from instructions.models import Instruction
from medicalreport.models import RedactedAttachment
import PyPDF2
from report.functions import redaction_image
#from silk.profiling.profiler import silk_profile
import subprocess
import io
import os
import uuid

from pdf2image import convert_from_bytes, convert_from_path


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = BASE_DIR + '/medicalreport/templates/medicalreport/reports/medicalreport.html'
TEMP_DIR = BASE_DIR + '/medi/static/generic_pdf/'
logger = logging.getLogger('timestamp')


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


def generate_redact_pdf(
        patient_first_name: str, patient_last_name: str,
        pdf_path: str = '', pdf_byte: bytes = b'', image_name: str = ''):

    images_name_list = []

    if pdf_byte:
        pages = convert_from_bytes(pdf_byte)
    elif pdf_path:
        pages = convert_from_path(pdf_path)
    else:
        pages = None

    if pages:
        # pdf case
        for num, page in enumerate(pages):
            file_name = TEMP_DIR + 'out_{unique}_{num}.jpg'.format(num=num, unique=uuid.uuid4().hex)
            page.save(file_name, 'JPEG')
            images_name_list.append(file_name)
    else:
        # image case
        if image_name:
            images_name_list.append(image_name)

    output_pdf_list = []
    total_redacted_count = 0
    for image in images_name_list:
        redacted_count, out_pdf_obj = redaction_image(
            image_path=image,
            east_path=BASE_DIR + '/config/frozen_east_text_detection.pb',
            patient_info={
                'first_name': patient_first_name,
                'last_name': patient_last_name
            }
        )
        total_redacted_count += redacted_count
        output_pdf_list.append(out_pdf_obj)

    output = PyPDF2.PdfFileWriter()
    for pdf in output_pdf_list:
        if pdf.isEncrypted:
            pdf.decrypt(password='')
        for page_num in range(pdf.getNumPages()):
            output.addPage(pdf.getPage(page_num))

    pdf_page_buf = io.BytesIO()
    output.write(pdf_page_buf)

    for name in images_name_list:
        os.remove(name)

    return total_redacted_count, pdf_page_buf


def tiff_processing(image: Image, max_pages: int=200) -> BytesIO:
    height = image.tag[0x101][0]
    width = image.tag[0x100][0]
    out_pdf_io = BytesIO()
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
    return out_pdf_io


class MedicalReport:

    @staticmethod
    def render(params: dict) -> HttpResponse:
        start_time = timezone.now()
        template = get_template(REPORT_DIR)
        html = template.render(params)
        response = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), response, link_callback=link_callback)
        end_time = timezone.now()
        total_time = end_time - start_time
        logger.info("[GENERATE PDF WITH XML] %s seconds with instruction %s"%(total_time.seconds, params.get('instruction')))
        if not pdf.err:
            return HttpResponse(response.getvalue(), content_type='application/pdf')
        else:
            return HttpResponse("Error Rendering PDF", status=400)

    @staticmethod
    def download(params: dict) -> HttpResponse:
        template = get_template(REPORT_DIR)
        html = template.render(params)
        file = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), file, link_callback=link_callback)

        if not pdf.err:
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="report.pdf"'
            response.write(file.getvalue())
            return response

    @staticmethod
    def get_pdf_file(params: dict, raw=False) -> ContentFile:
        template = get_template(REPORT_DIR)
        html = template.render(params)
        file = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), file, link_callback=link_callback)
        if not pdf.err:
            if raw:
                return file.getvalue()
            else:
                return ContentFile(file.getvalue())


class AttachmentReport:
    def __init__(self, instruction: Instruction, raw_xml: str, path_file: str):
        self.instruction = instruction
        self.path_file = path_file
        self.raw_xml = raw_xml
        self.file_name = Base64Attachment(self.raw_xml).filename()
        self.file_type = self.file_name.split('.')[-1]

    def render(self) -> HttpResponse:
        if self.file_type == "pdf":
            return self.render_pdf()
        elif self.file_type in ["rtf", "doc", "docx"]:
            return self.render_pdf_with_libreoffice()
        elif self.file_type in ["jpg", "jpeg", "png", "tiff", "tif"]:
            return self.render_image()
        else:
            return self.render_download_file(self.path_file, self.instruction.id)

    def download(self) -> HttpResponse:
        attachment = Base64Attachment(self.raw_xml).data()
        buffer = BytesIO()
        buffer.write(attachment)
        save_file = '%s_tmp_attachments.%s'%(self.instruction.pk, self.file_type)
        f = open(TEMP_DIR + save_file, 'wb')
        f.write(buffer.getvalue())
        f.close()
        download_file = open(TEMP_DIR + save_file, 'rb')
        response = HttpResponse(download_file, content_type="application/octet-stream")
        response['Content-Disposition'] = 'attachment; filename=' + self.file_name.split('\\')[-1]
        return response

    @staticmethod
    def render_download_file(dds_identifier, instruction_id) -> HttpResponse:
        link = reverse(
            'medicalreport:download_attachment',
            kwargs={'path_file': dds_identifier, 'instruction_id': instruction_id}
        )
        return render_to_response('medicalreport/preview_and_download.html', {'link': link})

    def render_error(self) -> HttpResponse:
        return render_to_response('errors/handle_errors_convert_file.html')

    def render_pdf(self) -> HttpResponse:
        attachment = Base64Attachment(self.raw_xml).data()
        pdf_page_buf = BytesIO()
        pdf_page_buf.write(attachment)
        if settings.IMAGE_REDACTION_ENABLED:
            redacted_count, pdf_page_buf = generate_redact_pdf(
                self.instruction.patient_information.patient_first_name,
                self.instruction.patient_information.patient_last_name,
                pdf_byte=attachment
            )

            if not RedactedAttachment.objects.filter(instruction_id=self.instruction.id, dds_identifier=self.path_file).exists():
                RedactedAttachment.objects.create(
                    instruction=self.instruction,
                    dds_identifier=self.path_file,
                    name=self.file_name,
                    raw_attachment_file_content=pdf_page_buf.getvalue(),
                    redacted_count=redacted_count
                )

        response = HttpResponse(
            pdf_page_buf.getvalue(),
            content_type="application/pdf",
        )

        return response

    def render_pdf_with_libreoffice(self) -> HttpResponse:
        attachment = Base64Attachment(self.raw_xml).data()
        buffer = BytesIO()
        buffer.write(attachment)
        tmp_file = '%s_tmp.%s'%(self.instruction.pk, self.file_type)
        f = open(TEMP_DIR + tmp_file, 'wb')
        f.write(buffer.getvalue())
        f.close()
        subprocess.call(
            ("export HOME=/tmp && libreoffice --headless --convert-to pdf --outdir " + TEMP_DIR + " " + TEMP_DIR + "/" + tmp_file),
            shell=True
        )
        pdf = open(TEMP_DIR + '%s_tmp.pdf' % self.instruction.pk, 'rb')
        redacted_pdf = None
        if settings.IMAGE_REDACTION_ENABLED:
            pdf_path = TEMP_DIR + '%s_tmp.pdf'%self.instruction.pk
            redacted_count, redacted_pdf = generate_redact_pdf(
                self.instruction.patient_information.patient_first_name,
                self.instruction.patient_information.patient_last_name,
                pdf_path=pdf_path
            )

            if not RedactedAttachment.objects.filter(instruction_id=self.instruction.id, dds_identifier=self.path_file).exists():
                RedactedAttachment.objects.create(
                    instruction=self.instruction,
                    dds_identifier=self.path_file,
                    name=self.file_name,
                    raw_attachment_file_content=redacted_pdf.getvalue(),
                    redacted_count=redacted_count
                )

        response = HttpResponse(
            redacted_pdf.getvalue() if redacted_pdf else pdf,
            content_type="application/pdf",
        )

        return response

    def render_image(self) -> HttpResponse:
        attachment = Base64Attachment(self.raw_xml).data()
        image = Image.open(BytesIO(attachment))
        image_format = image.format
        if image_format == "TIFF":
            return self.render_pdf_with_tiff(image)

        extension = str(image_format)
        response = HttpResponse(content_type="image/" + extension.lower())
        image.save(response, image_format)

        if settings.IMAGE_REDACTION_ENABLED:
            image_path = TEMP_DIR + 'out_{unique}_{num}.jpg'.format(num=1, unique=uuid.uuid4().hex)
            image.save(image_path)

            redacted_count, redacted_pdf = generate_redact_pdf(
                self.instruction.patient_information.patient_first_name,
                self.instruction.patient_information.patient_last_name,
                image_name=image_path
            )

            if not RedactedAttachment.objects.filter(instruction_id=self.instruction.id, dds_identifier=self.path_file).exists():
                RedactedAttachment.objects.create(
                    instruction=self.instruction,
                    dds_identifier=self.path_file,
                    name=self.file_name,
                    raw_attachment_file_content=redacted_pdf.getvalue(),
                    redacted_count=redacted_count
                )

            response = HttpResponse(
                redacted_pdf.getvalue(),
                content_type="application/pdf",
            )

        return response

    def render_pdf_with_tiff(self, image: Image, max_pages: int=200) -> HttpResponse:
        out_pdf_io = tiff_processing(image, max_pages)

        response = HttpResponse(
            out_pdf_io.getvalue(),
            content_type='application/pdf',
        )

        if settings.IMAGE_REDACTION_ENABLED:
            redacted_count, redacted_pdf = generate_redact_pdf(
                self.instruction.patient_information.patient_first_name,
                self.instruction.patient_information.patient_last_name,
                pdf_byte=out_pdf_io.getvalue()
            )

            if not RedactedAttachment.objects.filter(instruction_id=self.instruction.id, dds_identifier=self.path_file).exists():
                RedactedAttachment.objects.create(
                    instruction=self.instruction,
                    dds_identifier=self.path_file,
                    name=self.file_name,
                    raw_attachment_file_content=redacted_pdf.getvalue(),
                    redacted_count=redacted_count
                )

            response = HttpResponse(
                redacted_pdf.getvalue(),
                content_type="application/pdf",
            )

        return response
