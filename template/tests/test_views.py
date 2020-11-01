from django.test import TestCase
from model_mommy import mommy
from django.http import JsonResponse
from django.shortcuts import reverse
from accounts.models import User, ClientUser, Patient
from instructions.model_choices import INSTRUCTION_TYPE_CHOICES
from organisations.models import OrganisationClient
from snomedct.models import SnomedConcept
from template.models import (
    TemplateInstruction, TemplateAdditionalQuestion, TemplateAdditionalCondition
)
import os
from contextlib import suppress

class TemplateTestCase(TestCase):
    def setUp(self):
        user = mommy.make(User, username='client', first_name='client')
        organisation = mommy.make(OrganisationClient, trading_name="client_organisation")
        client_user = mommy.make(ClientUser, user=user)
        self.template_instruction1 = mommy.make(
            TemplateInstruction, template_title="template001",
            organisation=organisation, pk=1
        )
        self.template_instruction2 = mommy.make(
            TemplateInstruction, template_title="template002",
            organisation=organisation, pk=2
        )
        self.template_addition_question1=mommy.make(
            TemplateAdditionalQuestion,
            template_instruction=self.template_instruction1,
            question="questions_001"
        )
        self.template_addition_question2=mommy.make(
            TemplateAdditionalQuestion,
            template_instruction=self.template_instruction2,
            question="questions_002"
        )
        self.snomedct = mommy.make(
            SnomedConcept, fsn_description='fsn_description',
            external_id=11111
        )
        self.snomedct_external_ids = [111111,222222]
        self.template_conditions_of_interest = mommy.make(
            TemplateAdditionalCondition,
            template_instruction=self.template_instruction1,
            snomedct=self.snomedct
        )

    def tearDown(self):
        with suppress(FileNotFoundError, AttributeError, ValueError):
            os.remove(self.instruction.consent_form.path)

class CreateTemplateInstructionTest(TemplateTestCase):
    def test_create_template_instruction(self):
        self.assertEqual(
            str(self.template_instruction1),
            self.template_instruction1.template_title
        )


class CreateOrUpdateAdditionQuestionTest(TemplateTestCase):
    def test_create_or_update_addition_question(self):
        existing_question = self.template_addition_question2
        existing_question.delete()
        addition_question = mommy.make(
            TemplateAdditionalQuestion,
            template_instruction=self.template_instruction1,
            question="question_001"
        )
        existing_question = addition_question
        self.assertEqual('question_001', existing_question.question)


class CreateOrUpdateSnomedRelationsTest(TemplateTestCase):
    def test_create_or_update_snomed_relations(self):
        condition_code = 111111
        if condition_code in self.snomedct_external_ids:
            conditionofinterest = mommy.make(
                TemplateAdditionalCondition,
                template_instruction=self.template_instruction1,
                snomedct=self.snomedct
            )
            self.assertEqual(
                'fsn_description (11111)',
                "{} ({})".format(self.snomedct.fsn_description, self.snomedct.external_id)
            )


class TemplateViewsTest(TemplateTestCase):
    def test_view_template(self):
        response = self.client.get('/template/view-templates/')
        self.assertEqual(200, response.status_code)

    def test_new_template(self):
        response = self.client.get('/template/new-template/')
        self.assertEqual(200, response.status_code)

    def test_edit_template(self):
        response = self.client.get('/template/edit-template/1')
        self.assertEqual(200, response.status_code)

    def test_edit_returns_404_if_template_does_not_exist(self):
        response = self.client.get('/template/edit-template/3')
        self.assertEqual(404, response.status_code)

    def test_remove_template(self):
        response = self.client.get('/template/remove-template/2')
        self.assertEqual(302, response.status_code)

    def test_view_returns_404_if_template_does_not_exist(self):
        response = self.client.get('/template/remove-template/3')
        self.assertEqual(404, response.status_code)


class GetTemplateDataTest(TemplateTestCase):
    def test_get_template_data(self):
        response = self.client.get('/template/get-template-data/1')
        self.assertEqual(200, response.status_code)

    def test_get_template_returns_302_if_template_does_not_exist(self):
        response = self.client.get('/template/get-template-data/3')
        self.assertEqual(404, response.status_code)
