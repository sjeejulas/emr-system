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
#from silk.profiling.profiler import silk_profile
import subprocess


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = BASE_DIR + '/medicalreport/templates/accounts/info_template.html'
TEMP_DIR = BASE_DIR + '/medi/static/generic_pdf/'
logger = logging.getLogger('timestamp')


def link_callback(uri, rel):
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


class InfoInstructions:
    @staticmethod
    def render(params: dict):
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
    #@silk_profile(name='Get PDF Medical Report Method')
    def get_pdf_file(params: dict):
        template = get_template(REPORT_DIR)
        html = template.render(params)
        file = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), file, link_callback=link_callback)
        if not pdf.err:
            return ContentFile(file.getvalue())

