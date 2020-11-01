import os
import xhtml2pdf.pisa as pisa
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
import reportlab
import reportlab.lib.pagesizes as pdf_sizes
from django.conf import settings

BASE_DIR = settings.BASE_DIR
MDXCONSENT_DIR = settings.MDXCONSENT_DIR


def link_callback(uri: str, rel) -> str:
    sUrl = settings.STATIC_URL
    sRoot = settings.STATIC_ROOT

    if uri.startswith(sUrl):
        path = os.path.join(sRoot, uri.replace(sUrl, ""))

    path = BASE_DIR + '/' + path

    if not os.path.isfile(path):
        raise Exception('static URI must start with %s' % (sUrl))
    return path


class MDXDualConsent:

    @staticmethod
    def render(params: dict) -> HttpResponse:
        template = get_template(MDXCONSENT_DIR)
        html = template.render(params)
        response = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), response, link_callback=link_callback)
        if not pdf.err:
            return HttpResponse(response.getvalue(), content_type='application/pdf')
        else:
            return HttpResponse("Error Rendering PDF", status=400)
