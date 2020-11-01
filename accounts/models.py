from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractUser, Permission, Group
from django.template import loader
from django.utils.translation import gettext_lazy as _
from permissions.model_choices import MANAGER_PERMISSIONS, GP_PERMISSIONS,\
        OTHER_PERMISSIONS, CLIENT_ADMIN_PERMISSIONS, MEDI_PERMISSIONS, CLIENT_MANAGER_PERMISSIONS,\
        MEDI_ADMIN_PERMISSIONS, MEDI_TEAM_PERMISSIONS
from organisations.models import OrganisationGeneralPractice, OrganisationClient, OrganisationMedidata
from common.models import TimeStampedModel
from common.functions import multi_getattr, send_mail
from typing import Union

SEX_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female')
)

TITLE_CHOICE = (
    ('', '----'),
    ('DR', 'Dr.'),
    ('MR', 'Mr.'),
    ('MIS', 'Miss'),
    ('MS', 'Ms.'),
    ('MRS', 'Mrs.'),
    ('MX', 'Mx.'),
)

MEDIDATA_USER = 'MEDI'
CLIENT_USER = 'CLT'
GENERAL_PRACTICE_USER = 'GP'
PATIENT_USER = 'PAT'

USER_TYPE_CHOICES = (
    (MEDIDATA_USER, 'Medidata'),
    (CLIENT_USER, 'Client'),
    (GENERAL_PRACTICE_USER, 'General Practice'),
    (PATIENT_USER, 'Patient')
)

NEW_REPORT_REQUEST = "NEW"
DIGEST_REPORT_REQUESTS = "DIGEST"
NO_EMAIL = "NO"

NOTIFICATIONS = (
    (NEW_REPORT_REQUEST, 'Email me on each new report request'),
    (DIGEST_REPORT_REQUESTS, 'Email me a digest of report requests twice a day'),
    (NO_EMAIL, "Don't send me Incoming Report Notifications")
)


class MyUserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(
        verbose_name='email',
        max_length=255,
        unique=True,
    )
    type = models.CharField(max_length=4, choices=USER_TYPE_CHOICES)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    objects = MyUserManager()

    def get_query_set_within_organisation(self):
        if self.userprofilebase:
            if hasattr(self.userprofilebase, 'generalpracticeuser'):
                organisation = self.userprofilebase.generalpracticeuser.organisation
                return User.objects.filter(userprofilebase__generalpracticeuser__organisation=organisation)
            elif hasattr(self.userprofilebase, 'clientuser'):
                organisation = self.userprofilebase.clientuser.organisation
                return User.objects.filter(userprofilebase__clientuser__organisation=organisation)
            elif hasattr(self.userprofilebase, 'medidatauser'):
                return User.objects.filter(type__in=[MEDIDATA_USER, CLIENT_USER, GENERAL_PRACTICE_USER])
            else:
                return User.objects.all()
        else:
            return None

    def get_short_my_role(self) -> str:
        profile = self.userprofilebase
        if self.type == MEDIDATA_USER:
            return 'Medidata'
        elif self.type == CLIENT_USER and hasattr(profile, 'clientuser'):
            return profile.clientuser.get_role_display() or '--'
        elif self.type == GENERAL_PRACTICE_USER and hasattr(profile, 'generalpracticeuser'):
            return profile.generalpracticeuser.get_role_display() or '--'
        else:
            return 'Patient'

    def get_my_role(self) -> str:
        profile = self.userprofilebase
        if self.type == MEDIDATA_USER:
            return 'Medidata User'
        elif self.type == CLIENT_USER and hasattr(profile, 'clientuser'):
            role = profile.clientuser.role
            if role == ClientUser.CLIENT_MANAGER:
                return 'Client Manager'
            else:
                return 'Client Administrator'
        elif self.type == GENERAL_PRACTICE_USER and hasattr(profile, 'generalpracticeuser'):
            role = profile.generalpracticeuser.role
            if role == GeneralPracticeUser.PRACTICE_MANAGER:
                return 'General Practice Manager'
            elif role == GeneralPracticeUser.GENERAL_PRACTICE:
                return 'General Practice User'
            else:
                return 'Other Practice Stuff'
        else:
            return 'Patient User'

    def get_my_organisation(self) -> Union[OrganisationGeneralPractice, OrganisationMedidata, OrganisationClient, None]:
        if self.type == CLIENT_USER:
            organisation = self.userprofilebase.clientuser.organisation
        elif self.type == GENERAL_PRACTICE_USER:
            organisation = self.userprofilebase.generalpracticeuser.organisation
        elif self.type == MEDIDATA_USER:
            organisation = self.userprofilebase.medidatauser.organisation
        else:
            organisation = None
        return organisation

    def __str__(self):
        title = ''
        if hasattr(self, 'userprofilebase'):
            user_profile = self.userprofilebase
            title = user_profile.get_title_display()
        return ' '.join([title, self.first_name, self.last_name])

    def can_do_under(self) -> bool:
        client_organisation = multi_getattr(self, 'userprofilebase.clientuser.organisation', default=None)
        org = OrganisationClient
        types = [org.INSURER, org.REINSURER, org.OUTSOURCER]
        if client_organisation and client_organisation.type in types:
            return True
        return False

    def can_do_claim(self) -> bool:
        client_organisation = multi_getattr(self, 'userprofilebase.clientuser.organisation', default=None)
        org = OrganisationClient
        types = [
            org.INSURER, org.REINSURER, org.BROKER, org.SOLICITOR,
            org.OUTSOURCER, org.GOVERNMENT_AGENCY, org.PHARMACEUTICALS,
            org.RESEARCH, org.OTHER
        ]
        if client_organisation and client_organisation.type in types:
            return True
        return False

    def can_do_sars(self) -> bool:
        client_organisation = multi_getattr(self, 'userprofilebase.clientuser.organisation', default=None)
        gp_organisation = multi_getattr(self, 'userprofilebase.generalpracticeuser.organisation', default=None)
        org = OrganisationClient
        types = [
            org.BROKER, org.SOLICITOR, org.OUTSOURCER,
            org.GOVERNMENT_AGENCY, org.PHARMACEUTICALS,
            org.RESEARCH, org.OTHER
        ]
        if client_organisation and client_organisation.type in types:
            return True
        elif gp_organisation:
            return True
        return False


class UserProfileBase(TimeStampedModel, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=3, choices=TITLE_CHOICE)
    middle_name = models.CharField(max_length=255, blank=True)
    maiden_name = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address_name_number = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    address_line3 = models.CharField(max_length=255, blank=True)
    address_postcode = models.CharField(max_length=255, blank=True)
    address_country = models.CharField(max_length=255, blank=True)
    telephone_home = models.CharField(max_length=255, blank=True)
    telephone_mobile = models.CharField(max_length=255, blank=True)
    telephone_code = models.CharField(max_length=10, blank=True)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True)

    class Meta:
        verbose_name = 'User Profile Base'
        verbose_name_plural = 'User Profile Bases'

    def __str__(self):
        return self.user.email + "User Profile"

    def get_telephone_e164(self) -> str:
        phone = self.get_phone_without_zero(self.telephone_mobile)
        return "+%s%s"%(self.telephone_code, phone)

    def get_phone_without_zero(self, phone: str) -> str:
        if phone and phone[0] == '0':
            phone = phone[1:]
        return phone

    def remove_permission(self) -> None:
        for permission in self.user.user_permissions.all():
            self.user.user_permissions.remove(permission)

        for group in self.user.groups.all():
            self.user.groups.remove(group)

    def set_permission(self, permissions: list) -> None:
        for perm_codename in permissions:
            permission = Permission.objects.get(codename=perm_codename)
            self.user.user_permissions.add(permission)


class MedidataUser(UserProfileBase):
    MEDI_SUPER_USER = 0
    MEDI_ADMIN = 1
    MEDI_TEAM = 2

    ROLE_CHOICES = (
        ('', '----'),
        (MEDI_SUPER_USER, 'Medi Super User'),
        (MEDI_ADMIN, 'Medi Admin'),
        (MEDI_TEAM, 'Medi Team'),
    )

    role = models.IntegerField(choices=ROLE_CHOICES, null=True, blank=True, verbose_name='Role')
    organisation = models.ForeignKey(OrganisationMedidata, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Medidata User'

    def __str__(self):
        return 'Medidata' + self.user.first_name

    def __init__(self, *args, **kwargs):
        super(MedidataUser, self).__init__(*args, **kwargs)
        self.initial_role = self.role

    def save(self, *args, **kwargs):
        if self.initial_role != self.role or self._state.adding:
            self.update_permission()
        super(MedidataUser, self).save(*args, **kwargs)

    def update_permission(self) -> None:
        self.remove_permission()
        user = self.user
        user.is_staff = True
        user.is_superuser = False
        if self.role == self.MEDI_SUPER_USER:
            user.is_superuser = True
        elif self.role == self.MEDI_ADMIN:
            self.set_permission(MEDI_ADMIN_PERMISSIONS)
        else:
            self.set_permission(MEDI_TEAM_PERMISSIONS)
        user.save()


class ClientUser(UserProfileBase):
    CLIENT_MANAGER = 0
    CLIENT_ADMIN = 1

    ROLE_CHOICES = (
        ('', '----'),
        (CLIENT_MANAGER, 'Client Manager'),
        (CLIENT_ADMIN, 'Client Administrator')
    )

    role = models.IntegerField(choices=ROLE_CHOICES, null=True, blank=True, verbose_name='Role')
    organisation = models.ForeignKey(OrganisationClient, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Client User'

    def __str__(self):
        user = self.user
        return ' '.join([self.get_title_display(), user.first_name, user.last_name])

    def __init__(self, *args, **kwargs):
        super(ClientUser, self).__init__(*args, **kwargs)
        self.initial_role = self.role

    def save(self, *args, **kwargs):
        if self.role:
            self.role = int(self.role)
        if self.initial_role != self.role or self._state.adding:
            self.update_permission()
        super(ClientUser, self).save(*args, **kwargs)

    def update_permission(self) -> None:
        self.remove_permission()
        if self.role == self.CLIENT_MANAGER:
            self.update_permission_manager()
        else:
            self.update_permission_admin()

    def update_permission_manager(self) -> None:
        self.set_permission(CLIENT_MANAGER_PERMISSIONS)

    def update_permission_admin(self) -> None:
        self.set_permission(CLIENT_ADMIN_PERMISSIONS)


class GeneralPracticeUser(UserProfileBase):
    PRACTICE_MANAGER = 0
    GENERAL_PRACTICE = 1
    OTHER_PRACTICE = 2

    ROLE_CHOICES = (
        ('', '----'),
        (PRACTICE_MANAGER, 'Manager'),
        (GENERAL_PRACTICE, 'GP'),
        (OTHER_PRACTICE, 'Other practice staff')
    )

    role = models.IntegerField(choices=ROLE_CHOICES, null=True, blank=True, verbose_name='Role')
    organisation = models.ForeignKey(OrganisationGeneralPractice, on_delete=models.CASCADE)
    code = models.CharField(max_length=255, blank=True)
    payment_bank_holder_name = models.CharField(max_length=255, blank=True)
    payment_bank_account_number = models.CharField(max_length=255, blank=True)
    payment_bank_sort_code = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'General Practice User'

    def __str__(self):
        user = self.user
        return ' '.join([self.get_title_display(), user.first_name, user.last_name])

    def __init__(self, *args, **kwargs):
        super(GeneralPracticeUser, self).__init__(*args, **kwargs)
        self.initial_role = self.role
        self.initial_organisation_pk = None
        if hasattr(self, "organisation"):
            self.initial_organisation_pk = self.organisation.pk

    def save(self, *args, **kwargs):
        if self.role:
            self.role = int(self.role)
        if self.initial_role != self.role or self._state.adding or\
            self.initial_organisation_pk != self.organisation.pk:
            self.update_permission()
        if self._state.adding:
            self.sending_surgery_email()
        super(GeneralPracticeUser, self).save(*args, **kwargs)

    def sending_surgery_email(self) -> None:
        if self.organisation and self.organisation.organisation_email:
            html_message = loader.render_to_string('accounts/email_message_new_user.html', {
                'name': self.user.get_full_name(),
                'role': self.get_role_display()
            })
            send_mail(
                'eMR New user',
                '',
                'MediData',
                [self.organisation.organisation_email],
                fail_silently=True,
                html_message=html_message,
            )

    def update_permission(self) -> None:
        self.remove_permission()
        group_name = "%s : %s"%(self.get_role_display(),self.organisation.__str__())
        for group in Group.objects.filter(name=group_name):
            self.user.groups.add(group)

        if self.role == self.PRACTICE_MANAGER:
            self.update_permission_manager()
        elif self.role == self.GENERAL_PRACTICE:
            self.update_permission_gp()
        else:
            self.update_permission_other()

    def update_permission_manager(self) -> None:
        self.set_permission(MANAGER_PERMISSIONS)

    def update_permission_gp(self) -> None:
        self.set_permission(GP_PERMISSIONS)

    def update_permission_other(self) -> None:
        self.set_permission(OTHER_PERMISSIONS)


class PracticePreferences(models.Model):
    gp_organisation = models.OneToOneField(OrganisationGeneralPractice, on_delete=models.CASCADE)
    notification = models.CharField(default=NEW_REPORT_REQUEST, choices=NOTIFICATIONS, max_length=20)
    contact_feedback = models.BooleanField(default=False)
    contact_updates = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'GP Practice Preferences'

    def __str__(self):
        return self.gp_organisation.name + " Preferences"


class Patient(UserProfileBase):
    organisation_gp = models.ForeignKey(OrganisationGeneralPractice, on_delete=models.CASCADE, null=True)
    nhs_number = models.CharField(max_length=10, blank=True)
    emis_number = models.CharField(max_length=255, blank=True)
    vision_number = models.CharField(max_length=255, blank=True)
    systmone_number = models.CharField(max_length=255, blank=True)
    microtest_number = models.CharField(max_length=255, blank=True)
    patient_input_email = models.EmailField(max_length=255, blank=True)
    alternate_phone = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Patient User'

    def __str__(self):
        return self.user.first_name        


class Whitelist(models.Model):
    from_ip = models.GenericIPAddressField()
    to_ip   = models.GenericIPAddressField()

    class Meta:
        verbose_name = 'Whitelist'

    def __str__(self):
        return ','.join([self.from_ip, self.to_ip])

    def get_all_objects(self):
        queryset = self._meta.model.objects.all().values_list('from_ip', 'to_ip')

        return queryset
