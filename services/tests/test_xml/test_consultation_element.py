from services.tests.xml_test_case import XMLTestCase

from services.xml.consultation_element import (
    GenericContent, ConsultationElement
)
from services.xml.value_event import ValueEvent
from services.xml.allergy_event import AllergyEvent
from services.xml.referral_event import ReferralEvent
from services.xml.problem import Problem


class GenericContentTest(XMLTestCase):
    def setUp(self):
        super().setUp(ConsultationElement.XPATH)
        consultation_elements = [ConsultationElement(e) for e in self.elements]
        self.generic_content = consultation_elements[0].content()
        self.assertIsInstance(self.generic_content, GenericContent)

    def test_string_representation(self):
        self.assertEqual('GenericContent', str(self.generic_content))

    def test_description(self):
        self.assertEqual('Non-smoker', self.generic_content.description())


class ConsultationElementTest(XMLTestCase):
    def setUp(self):
        super().setUp(ConsultationElement.XPATH)
        self.consultation_elements = [
            ConsultationElement(e) for e in self.elements
        ]

    def test_header(self):
        self.assertEqual('Social', self.consultation_elements[0].header())

    def test_display_order(self):
        self.assertEqual(0, self.consultation_elements[0].display_order())

    def test_content_when_in_content_classes(self):
        for ce in self.consultation_elements[2:11]:
            self.assertTrue(isinstance(ce.content(), ValueEvent))
        self.assertTrue(
            isinstance(self.consultation_elements[29].content(), AllergyEvent)
        )
        self.assertTrue(
            isinstance(self.consultation_elements[30].content(), ReferralEvent)
        )

    def test_content_when_not_in_content_classes(self):
        for ce in self.consultation_elements[:2]:
            self.assertTrue(isinstance(ce.content(), GenericContent))

    def test_problem_returns_problem_if_problem_tag_is_present(self):
        self.assertTrue(
            isinstance(self.consultation_elements[12].problem(), Problem)
        )

    def test_problem_returns_none_if_problem_tag_is_not_present(self):
        self.assertIsNone(self.consultation_elements[0].problem())

    def test_is_significant_problem(self):
        self.assertTrue(
            self.consultation_elements[12].is_significant_problem()
        )

    def test_is_significant_problem_returns_false_when_problem_is_none(self):
        self.assertFalse(
            self.consultation_elements[0].is_significant_problem()
        )

    def test_is_significant_problem_returns_false_if_not_significant(self):
        self.assertFalse(
            self.consultation_elements[17].is_significant_problem()
        )
