from django.test import TestCase, Client
from django.shortcuts import reverse
from django.http import HttpResponse

from model_mommy import mommy

from organisations.models import OrganisationGeneralPractice
from accounts.models import User, GENERAL_PRACTICE_USER, GeneralPracticeUser
from services.views import handler_404, handler_500


class exceptionCode(TestCase):
    def setUp(self):
        self.gp_practice = mommy.make(
            OrganisationGeneralPractice,
            practcode='TEST0001',
            name='Test Surgery',
            operating_system_organisation_code=10000,
        )

        self.gp_user = mommy.make(User, email='gp_user1@gmail.com', password='secret', type=GENERAL_PRACTICE_USER, )

        self.gp_manager = mommy.make(
            GeneralPracticeUser,
            user=self.gp_user,
            organisation=self.gp_practice,
            role=GeneralPracticeUser.PRACTICE_MANAGER
        )
    
    def test_get_404(self):
        self.client.force_login(self.gp_user)
        client = Client()
        response = client.get('/what/the/url')
        self.assertEqual(404, response.status_code)
        self.assertTemplateUsed(response, 'errors/handle_errors.html')

    def test_get_500(self):
        self.client.force_login(self.gp_user)
        response = HttpResponse(status=500)
        self.assertEqual(500, response.status_code)