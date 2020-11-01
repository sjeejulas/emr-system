from django.test import TestCase

from model_mommy import mommy

from organisations.models import (
    OrganisationMedidata, OrganisationBase, OrganisationClient,
    OrganisationGeneralPractice,
)

import string
import random


class OrganisationMedidataTest(TestCase):
    def test_string_representation(self):
        organisation_medidata = mommy.make(
            OrganisationMedidata, trading_name='trading_name'
        )
        self.assertEqual(str(organisation_medidata), 'trading_name')


class OrganisationBaseTest(TestCase):
    def test_string_representation(self):
        organisation_base = mommy.make(
            OrganisationBase, trading_name='trading_name'
        )
        self.assertEqual(str(organisation_base), 'trading_name')


class OrganisationClientTest(TestCase):
    def test_string_representation(self):
        organisation_client = mommy.make(
            OrganisationClient, trading_name='trading_name'
        )
        self.assertEqual(str(organisation_client), 'trading_name')


class OrganisationGeneralPracticeTest(TestCase):
    def setUp(self):
        self.organisation_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        self.organisation_general_practice = mommy.make(
            OrganisationGeneralPractice, name='trading_name',
            operating_system_salt_and_encrypted_password=self.organisation_password ,
        )

    def test_string_representation(self):
        self.assertEqual(str(self.organisation_general_practice), 'trading_name')

    def test_set_operating_system_salt_and_encrypted_password(self):
        self.assertNotEqual(
            self.organisation_password,
            self.organisation_general_practice._operating_system_salt_and_encrypted_password
        )

    def test_get_operating_system_salt_and_encrypted_password(self):
        self.assertEqual(
            self.organisation_password,
            self.organisation_general_practice.operating_system_salt_and_encrypted_password
        )
