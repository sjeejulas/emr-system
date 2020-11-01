from django.contrib import admin
from .models import PatientReportAuth, ThirdPartyAuthorisation, UnsupportedAttachment
from common.functions import send_mail


class ThirdPartyAuthorisationAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):

        if obj.expired:
            send_mail(
                'Medical Report Authorisation Expired',
                'Your access to the SAR report for {ref_number} has expired. Please contact your client if a third party access extension is required.'.format(
                    ref_number=obj.patient_report_auth.patient_report_auth.instruction.medi_ref,
                ),
                'Medidata',
                [obj.email],
                fail_silently=True
            )
            super().save_model(request, obj, form, change)


class UnsupportedAttachmentAdmin(admin.ModelAdmin):

    list_display = ('instruction', 'file_name', 'file_type')

admin.site.register(PatientReportAuth)
admin.site.register(ThirdPartyAuthorisation, ThirdPartyAuthorisationAdmin)
admin.site.register(UnsupportedAttachment, UnsupportedAttachmentAdmin)
