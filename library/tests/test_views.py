from django.test import TestCase
from django.shortcuts import reverse

from model_mommy import mommy

from organisations.models import OrganisationGeneralPractice
from accounts import models as account_models
from library.models import Library


class TestLibraryBase(TestCase):

    def setUp(self):
        self.gp_practice_1 = mommy.make(
            OrganisationGeneralPractice,
            practcode='TEST0001',
            name='Test Surgery',
            operating_system_organisation_code=29390,
            operating_system_username='michaeljtbrooks',
            operating_system_salt_and_encrypted_password='Medidata2019',
        )
        self.gp_user = mommy.make(account_models.User, email='gp_user1@gmail.com', password='test1234',
                                  type=account_models.GENERAL_PRACTICE_USER)
        self.gp_manager_1 = mommy.make(
            account_models.GeneralPracticeUser,
            user=self.gp_user,
            organisation=self.gp_practice_1,
            role=account_models.GeneralPracticeUser.PRACTICE_MANAGER
        )

        self.library = mommy.make(Library, key='test_key', value='test value')


class TestLibraryView(TestLibraryBase):

    def test_access_library(self):
        self.client.force_login(self.gp_user)
        response = self.client.get(reverse('library:edit_library', kwargs={'event': 'index'}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'library/edit_library.html')
        self.client.logout()

    def test_add_library(self):
        self.client.force_login(self.gp_user)
        post_data = {
            'key': 'father',
            'value': '[ RELATION REDACTED ]'
        }
        response = self.client.post(reverse('library:edit_library', kwargs={'event': 'index'}), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Library.objects.filter(key='father', value='[ RELATION REDACTED ]'))
        self.client.logout()

    def test_delete_libray(self):
        self.client.force_login(self.gp_user)
        response = self.client.post(reverse('library:delete_library', kwargs={'library_id': self.library.id}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Library.objects.filter(id=self.library.id).exists())
        self.client.logout()

    def test_edit_library(self):
        self.client.force_login(self.gp_user)
        post_data = {
            'key': 'mother',
            'value': '[ RELATION REDACTED ]'
        }
        response = self.client.post(reverse('library:edit_word_library', kwargs={'library_id': self.library.id}), post_data)
        edited_library = Library.objects.get(id=self.library.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual('mother', edited_library.key)
        self.assertEqual('[ RELATION REDACTED ]', edited_library.value)
        self.client.logout()
