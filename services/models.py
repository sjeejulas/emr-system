from django.db import models
from accounts.models import MEDIDATA_USER, CLIENT_USER, GENERAL_PRACTICE_USER, PATIENT_USER


class SiteAccessControl(models.Model):
    site_host = models.CharField(max_length=255)
    gp_access = models.BooleanField(default=False)
    client_access = models.BooleanField(default=False)
    patient_access = models.BooleanField(default=True)
    medi_access = models.BooleanField(default=True)
    active_host = models.BooleanField(default=True)

    def __str__(self):
        return self.site_host

    def detail_role_access(self) -> str:
        access_list = list()
        if self.gp_access:
            access_list.append('GP')
        if self.client_access:
            access_list.append('CLT')
        if self.medi_access:
            access_list.append('MEDI')
        if self.patient_access:
            access_list.append('PAT')
        return " / ".join(access_list)

    def can_access_site(self, user_type) -> bool:
        if self.active_host:
            if user_type == GENERAL_PRACTICE_USER and self.gp_access:
                return True
            elif user_type == CLIENT_USER and self.client_access:
                return True
            elif user_type == MEDIDATA_USER and self.medi_access:
                return True
            elif user_type == PATIENT_USER and self.patient_access:
                return True
            else:
                return False
        else:
            return False