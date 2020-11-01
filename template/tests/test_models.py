from django.test import TestCase
from accounts.models import User, ClientUser, Patient
from instructions.model_choices import INSTRUCTION_TYPE_CHOICES
from organisations.models import OrganisationClient
from snomedct.models import SnomedConcept

from model_mommy import mommy

from template.models import (
    TemplateInstruction, TemplateAdditionalQuestion, TemplateAdditionalCondition
)


class TemplateInstructionTest(TestCase):
    def setUp(self):
        user = mommy.make(User, username='client', first_name='client')
        organisation = mommy.make(OrganisationClient, trading_name="client_organisation")
        client_user = mommy.make(ClientUser, user=user)
        self.template_instruction = mommy.make(
            TemplateInstruction, template_title="template001",
            organisation=organisation
        )

    def test_string_representation(self):
        temp_instruction_string = str(self.template_instruction)
        title = self.template_instruction.template_title
        self.assertEqual(
            temp_instruction_string,
            '{title}'.format(title=title)
        )


class TemplateAdditionalQuestionTest(TemplateInstructionTest):
    def setUp(self):
        super().setUp()
        self.template_addition_question=mommy.make(
            TemplateAdditionalQuestion,
            template_instruction=self.template_instruction,
            question="questions_001"
        )
    def test_string_representation(self):
        question_string = str(self.template_addition_question)
        question = self.template_addition_question.question
        self.assertEqual(
            question_string,
            '{question}'.format(question=question)
        )


class TemplateAdditionalConditionTest(TemplateInstructionTest):
    def setUp(self):
        super().setUp()
        self.snomedct = mommy.make(
            SnomedConcept, fsn_description='fsn_description',
            external_id=1234567890
        )
        self.template_conditions_of_interest = mommy.make(
            TemplateAdditionalCondition,
            template_instruction=self.template_instruction,
            snomedct=self.snomedct
        )
    def test_string_representation(self):
        condition_string = str(self.template_conditions_of_interest)
        self.assertEqual(condition_string,
            "{} - {}".format(self.snomedct.external_id, self.snomedct.fsn_description)
        )
