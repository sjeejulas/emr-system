from django.db import models
from common.models import TimeStampedModel
from common.functions import get_env_variable, aes_with_salt_encryption, aes_with_salt_decryption
import random, string, logging

AES_KEY = get_env_variable('AES_KEY')

logger = logging.getLogger(__name__)


class OrganisationBase(models.Model):
    trading_name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255)
    address = models.TextField(max_length=255)
    created_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Organisation'
        permissions = (
            ('view_user_management', 'Can view User Management'),
            ('add_user_management', 'Can add User Management'),
            ('change_user_management', 'Can change User Management'),
            ('delete_user_management', 'Can delete User Management')
        )

    def __str__(self):
        return self.trading_name


class OrganisationMedidata(OrganisationBase):
    payment_bank_holder_name = models.CharField(max_length=255, blank=True)
    payment_bank_account_number = models.CharField(max_length=255, blank=True)
    payment_bank_sort_code = models.CharField(max_length=255, blank=True)
    
    class Meta:
        verbose_name = 'Organisation Medidata'

    def __str__(self):
        return self.trading_name


class OrganisationClient(OrganisationBase):
    INSURER = 1
    REINSURER = 2
    BROKER = 3
    SOLICITOR = 4
    OUTSOURCER = 5
    GOVERNMENT_AGENCY = 6
    PHARMACEUTICALS = 7
    RESEARCH = 8
    OTHER = 9

    ROLE_CHOICES = (
        (INSURER, 'Insurer'),
        (REINSURER, 'Reinsurer'),
        (BROKER, 'Broker'),
        (SOLICITOR, 'Solicitor'),
        (OUTSOURCER, 'Outsourcer'),
        (GOVERNMENT_AGENCY, 'Government agency'),
        (PHARMACEUTICALS, 'Pharmaceuticals'),
        (RESEARCH, 'Research'),
        (OTHER, 'Other')
    )

    type = models.IntegerField(choices=ROLE_CHOICES)
    fca_number = models.CharField(max_length=255, blank=True)
    division = models.TextField(blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_telephone = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    generic_telephone = models.CharField(max_length=255, blank=True)
    generic_email = models.EmailField(blank=True)
    fax_number = models.CharField(max_length=255, blank=True)
    companies_house_number = models.CharField(max_length=255, blank=True)
    vat_number = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Organisation Client'

    def __str__(self):
        return self.trading_name


class OrganisationGeneralPractice(models.Model):
    GP_OP_SYS_CHOICES = (
        ('EMISWeb', 'EMIS-Web'),
        ('HealthyV5', 'Healthy V5'),
        ('LV', 'EMIS-LV'),
        ('PCS', 'PCS'),
        ('Practice Manager', 'Practice Manager'),
        ('PREMIERE', 'Premiere'),
        ('SYNERGY', 'Synergy'),
        ('SystmOne', 'SystmOne'),
        ('Vision 3', 'Vision 3'),
        ('VA', 'Vision Anywhere'),
        ('MT', 'Microtest'),
        ('OT', 'Other')
    )

    PAYMENT_TIMING_CHOICES = (
        ('AR', 'Arrears'),
        ('AD', 'Advance')
    )
    region = models.CharField(max_length=255, blank=True)
    comm_area = models.CharField(max_length=255, blank=True)
    practcode = models.CharField(max_length=255, primary_key=True, unique=True)
    name = models.CharField(max_length=255, blank=True)
    billing_address_street = models.CharField(max_length=255, blank=True)
    billing_address_city = models.CharField(max_length=22, blank=True)
    billing_address_line_2 = models.CharField(max_length=255, blank=True)
    billing_address_line_3 = models.CharField(max_length=255, blank=True)
    billing_address_state = models.CharField(max_length=16, blank=True)
    billing_address_postalcode = models.CharField(max_length=8, blank=True)
    phone_office = models.CharField(max_length=28, blank=True)
    phone_alternate = models.CharField(max_length=20, blank=True)
    phone_onboarding_setup = models.CharField(max_length=28, blank=True, verbose_name='Set-Up Contact Number')
    organisation_email = models.CharField(max_length=255, blank=True)
    practicemanagername_c = models.CharField(max_length=34, blank=True)
    practicemanager_job_title = models.CharField(max_length=47, blank=True)
    practicemanager_email = models.CharField(max_length=54, blank=True)
    practicemanager_phone = models.CharField(max_length=28, blank=True)
    patientlistsize_c = models.CharField(max_length=255, blank=True)
    sitenumber_c = models.CharField(max_length=255, blank=True)
    employees = models.CharField(max_length=2, blank=True)
    ownership = models.CharField(max_length=45, blank=True)
    ccg_health_board_c = models.CharField(max_length=47, blank=True)
    fax = models.CharField(max_length=47, blank=True)
    gp_operating_system = models.CharField(max_length=32, choices=GP_OP_SYS_CHOICES, blank=True)
    website = models.CharField(max_length=255, blank=True)

    operating_system_socket_endpoint = models.CharField(max_length=255, blank=True)
    operating_system_organisation_code = models.CharField(max_length=63, blank=True)
    operating_system_username = models.CharField(max_length=255, blank=True)
    _operating_system_salt_and_encrypted_password = models.CharField(max_length=511, blank=True)
    operating_system_salt_and_encrypted_iv = models.CharField(max_length=255, blank=True)
    operating_system_auth_token = models.CharField(max_length=255, blank=True)

    payment_timing = models.CharField(max_length=2, choices=PAYMENT_TIMING_CHOICES, default = 'AR', blank=True)
    payment_bank_holder_name = models.CharField(max_length=255, blank=True)
    payment_bank_sort_code = models.CharField(max_length=255, blank=True)
    payment_bank_account_number = models.CharField(max_length=255, blank=True)
    payment_preference = models.CharField(max_length=255, blank=True)

    onboarding_by = models.CharField(max_length=255, blank=True)
    onboarding_job_title = models.CharField(max_length=255, blank=True)
    accept_policy = models.BooleanField(default=False)
    live = models.BooleanField(default=False)
    live_timechecked = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Organisation GeneralPractice'

    def __str__(self):
        return self.name

    def set_operating_system_salt_and_encrypted_password(self, val: str) -> None:
        salt = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        iv_salt, iv_aes_key, ciphertext = aes_with_salt_encryption(val, salt)
        self.operating_system_salt_and_encrypted_iv = '{iv_salt}${iv_aes_key}'.format(
            iv_salt=iv_salt, iv_aes_key=iv_aes_key
        )
        self._operating_system_salt_and_encrypted_password = '{salt}${aes_ciphertext}'.format(
            salt=salt, aes_ciphertext=ciphertext
        )

    def get_operating_system_salt_and_encrypted_password(self) -> str:
        if self.operating_system_salt_and_encrypted_iv:
            return aes_with_salt_decryption(
                self._operating_system_salt_and_encrypted_password,
                self.operating_system_salt_and_encrypted_iv,
            )
        return self._operating_system_salt_and_encrypted_password

    operating_system_salt_and_encrypted_password = property(
        get_operating_system_salt_and_encrypted_password,
        set_operating_system_salt_and_encrypted_password
    )

    def is_active(self) -> bool:
        return self.live and self.accept_policy

