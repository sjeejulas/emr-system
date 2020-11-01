from django.test import TestCase, Client
from django.shortcuts import reverse

from model_mommy import mommy

from organisations.models import OrganisationGeneralPractice
from accounts.models import GeneralPracticeUser, User, GENERAL_PRACTICE_USER

import json


class OnboardingHackingURLTestCase(TestCase):
    def setUp(self):
        self.active_gp_practice = mommy.make(OrganisationGeneralPractice, practcode='GP0002', live=True, accept_policy=True)
        self.active_user = mommy.make(User, email='activeuser@testmail.com', password='test1234', type=GENERAL_PRACTICE_USER)
        self.active_practice_manager = mommy.make(GeneralPracticeUser, user=self.active_user, organisation=self.active_gp_practice)
        self.inactice_gp_practice = mommy.make(OrganisationGeneralPractice, practcode='GP0001', live=False)
        self.inactive_user = mommy.make(User, email='inactiveuser@testmail.com', password='test1234', type=GENERAL_PRACTICE_USER)
        self.practice_manager = mommy.make(GeneralPracticeUser, user=self.inactive_user, organisation=self.inactice_gp_practice)

    def test_logged_in_hacking_emis_setup_views(self):
        self.client.force_login(self.active_user)
        response = self.client.get('/onboarding/step-3/GP0001')
        self.assertEqual(302, response.status_code)
        self.assertEqual('/accounts/login/', response.url)
        self.client.logout()

    def test_non_logged_in_hacking_emis_setup_views(self):
        response = self.client.get('/onboarding/step-3/GP0001')
        self.assertEqual(302, response.status_code)
        self.assertEqual('/accounts/login?next=/onboarding/step-3/GP0001', response.url)

    def test_non_active_user_redirect_from_pipeline_views_to_emis_setup(self):
        self.client.force_login(self.inactive_user)
        response = self.client.get('/instruction/view-pipeline/')
        self.assertEqual(302, response.status_code)
        self.assertEqual('/onboarding/step-3/GP0001', response.url)
        self.client.logout()

    def test_success_access_emis_setup_views(self):
        self.client.force_login(self.inactive_user)
        response = self.client.get('/onboarding/step-3/GP0001')
        self.assertEqual(200, response.status_code)
        self.client.logout()


class OnboardingSignUPTest(TestCase):

    def setUp(self):
        self.gp_practitioner_info = {
            'title': 'DR',
            'first_name': 'Sarah',
            'surname': 'Giles',
            'email': 'sarah@gmail.com',
            'password': 'sarah20182019',
            'telephone_mobile': '874432803',
            'telephone_code': '66',
        }
        self.gp_practice_info = {
            'surgery_name': 'Test Surgery 01',
            'practice_code': 'TEST0001',
            'postcode': 'TA10 0AB',
            'address_line1': 'Moortown Cottage',
            'city': 'Langport',
            'county': 'Somerset',
            'contact_num': '0800 0808',
            'emis_org_code': '29390',
            'operating_system': 'EMISWeb',
            'organisation_email': 'sarah@gmail.com',
            'confirm_email': 'sarah@gmail.com',
        }

        self.gp_practitioner_info_2 = {
            'title': 'DR',
            'first_name': 'Alan',
            'surname': 'Chatterly',
            'email': 'alan@gmail.com',
            'password': 'alannn20182019',
            'telephone_mobile': '874432803',
            'telephone_code': '66'
        }

        self.gp_practice_info_2 = {
            'surgery_name': 'Test Surgery 02',
            'practice_code': 'TEST0002',
            'postcode': 'TA10 0AB',
            'address_line1': 'Moortown Cottage',
            'city': 'Langport',
            'county': 'Somerset',
            'contact_num': '0800 0808',
            'emis_org_code': '29390',
            'operating_system': 'LV',
        }

    def test_get_view_step1(self):
        response = self.client.get(reverse('onboarding:step1'))

        self.assertEqual(response.status_code, 200)

    def test_post_view_sign_up_emis_system(self):
        response = self.client.post(reverse('onboarding:step1'), {
            'surgery_name': self.gp_practice_info['surgery_name'],
            'practice_code': self.gp_practice_info['practice_code'],
            'postcode': self.gp_practice_info['postcode'],
            'address_line1': self.gp_practice_info['address_line1'],
            'city': self.gp_practice_info['city'],
            'county': self.gp_practice_info['county'],
            'contact_num': self.gp_practice_info['contact_num'],
            'emis_org_code': self.gp_practice_info['emis_org_code'],
            'operating_system': self.gp_practice_info['operating_system'],
            'organisation_email': self.gp_practice_info['organisation_email'],
            'confirm_email': self.gp_practice_info['confirm_email'],
            'accept_policy': True,
            'consented': True
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/onboarding/step-2/TEST0001')
        self.assertTrue(
            OrganisationGeneralPractice.objects.filter(practcode=self.gp_practice_info['practice_code']).exists()
        )

        response = self.client.post(reverse('onboarding:step2', kwargs={'practice_code': self.gp_practice_info['practice_code']}), {
            'title': self.gp_practitioner_info['title'],
            'first_name': self.gp_practitioner_info['first_name'],
            'surname': self.gp_practitioner_info['surname'],
            'email1': self.gp_practitioner_info['email'],
            'email2': self.gp_practitioner_info['email'],
            'password1': self.gp_practitioner_info['password'],
            'password2': self.gp_practitioner_info['password'],
            'telephone_mobile': self.gp_practitioner_info['telephone_mobile'],
            'telephone_code': self.gp_practitioner_info['telephone_code'],
            'form-TOTAL_FORMS': '4',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-title': 'DR',
            'form-0-first_name': 'test1',
            'form-0-last_name': 'test1',
            'form-0-email': 'test20@gmail.com',
            'form-0-role': '0',
            'form-0-mobile_code': '66',
            'form-0-mobile_phone': '123456789',
            'form-1-title': 'DR',
            'form-1-first_name': 'test2',
            'form-1-last_name': 'test2',
            'form-1-email': 'test21@gmail.com',
            'form-1-role': '1',
            'form-1-mobile_code': '66',
            'form-1-mobile_phone': '123456789',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            User.objects.filter(email=self.gp_practitioner_info['email']).exists()
        )
        self.assertEqual(response.url, '/onboarding/step-3/TEST0001')

    def test_post_view_sign_up_other_system(self):
        response = self.client.post(reverse('onboarding:step1'), {
            'surgery_name': self.gp_practice_info_2['surgery_name'],
            'practice_code': self.gp_practice_info_2['practice_code'],
            'postcode': self.gp_practice_info_2['postcode'],
            'address_line1': self.gp_practice_info_2['address_line1'],
            'city': self.gp_practice_info_2['city'],
            'county': self.gp_practice_info_2['county'],
            'contact_num': self.gp_practice_info_2['contact_num'],
            'emis_org_code': self.gp_practice_info_2['emis_org_code'],
            'operating_system': self.gp_practice_info_2['operating_system'],
            'accept_policy': True,
            'consented': True
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/emr_message.html')
        self.assertContains(
            response,
            '<p>Thank you for completing part one of the eMR registration process. It’s great to have you on board.</p>'
        )
        self.assertContains(
            response,
            '<p>We will be in touch with you shortly to complete the set up process so that you can process SARs in seconds.</p>'
        )
        self.assertContains(
            response,
            '<p>We look forward to working with you in the very near future. eMR Support Team</p>'
        )


class OnboardingBaseTest(TestCase):

    def setUp(self):
        self.inactice_gp_practice = mommy.make(
            OrganisationGeneralPractice,
            name='Test Surgery03',
            practcode='TEST0003',
            operating_system_organisation_code='29390',
            gp_operating_system='LV',
            live=False
        )
        self.inactive_user = mommy.make(
            User,
            email='inactiveuser@testmail.com',
            password='test1234',
            type=GENERAL_PRACTICE_USER
        )
        self.practice_manager = mommy.make(
            GeneralPracticeUser,
            user=self.inactive_user,
            organisation=self.inactice_gp_practice
        )


class OnboardingEmisSetUpTest(OnboardingBaseTest):

    def test_get_emis_setup_view(self):
        self.client.force_login(self.inactive_user)
        response = self.client.get(
            reverse('onboarding:step3', kwargs={'practice_code': self.inactice_gp_practice.practcode})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/step3.html')
        self.client.logout()

    def test_post_emis_setup_view(self):
        self.client.force_login(self.inactive_user)
        response = self.client.post(
            reverse('onboarding:step3', kwargs={'practice_code': self.inactice_gp_practice.practcode}),
            {
                'surgery_name': self.inactice_gp_practice.name,
                'surgery_code': self.inactice_gp_practice.practcode,
                'emis_org_code': '111111',
                'operating_system': 'EMISWeb'
            }
        )

        self.assertEqual(response.status_code, 200)
        gp_practice_updated = OrganisationGeneralPractice.objects.get(practcode='TEST0003')
        self.assertEqual(gp_practice_updated.operating_system_organisation_code, '111111')
        self.assertEqual(gp_practice_updated.gp_operating_system, 'EMISWeb')
        self.client.logout()


class OnboardingEmrSetUpFinal(OnboardingBaseTest):

    def test_get_emr_setup_final_view(self):
        self.client.force_login(self.inactive_user)
        response = self.client.get(
            reverse('onboarding:step3', kwargs={'practice_code': self.inactice_gp_practice.practcode})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/step3.html')
        self.client.logout()


class EmisPollingTest(OnboardingBaseTest):

    def test_call_ajax_emis_polling(self):
        response = self.client.get(
            reverse('onboarding:emis_polling', kwargs={'practice_code': self.inactice_gp_practice.practcode})
        )

        response_content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_content['status'], 401)
        self.assertEqual(response_content['practice_code'], 'TEST0003')
