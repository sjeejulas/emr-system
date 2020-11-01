from django.db import models
from accounts.models import GeneralPracticeUser
from organisations.models import OrganisationGeneralPractice
from django.contrib.auth.models import Group


class InstructionPermission(models.Model):
    role = models.IntegerField(choices=GeneralPracticeUser.ROLE_CHOICES, verbose_name='Role', null=True)
    organisation = models.ForeignKey(OrganisationGeneralPractice, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    global_permission = models.BooleanField(default=False)

    class Meta:
        unique_together = ["role", "organisation", "group"]

    def __str__(self):
        return '%s : %s'%(self.get_role_display(),self.organisation.__str__())

    def allocate_permission_to_gp(self) -> None:
        for gp in GeneralPracticeUser.objects.filter(organisation=self.organisation, role=self.role):
            gp.user.groups.add(self.group)
