from services.tests.xml_test_case import XMLTestCase

from services.autoredactors.date_redactor import DateRedactor
from services.xml.consultation import Consultation

from datetime import date


class DateRedactorTest(XMLTestCase):
    def setUp(self):
        super().setUp(Consultation.XPATH)
        self.consultations = [Consultation(e) for e in self.elements]

    def test_is_redact_returns_true_if_parsed_date_is_before_start_date(self):
        date_redactor = DateRedactor(date(2019, 1, 1))
        consultation = self.consultations[0]
        self.assertIsInstance(consultation.parsed_date(), date)
        self.assertTrue(date_redactor.is_redact(consultation))

    def test_is_redact_returns_false_if_parsed_date_is_none(self):
        date_redactor = DateRedactor(date(2018, 1, 1))
        consultation = self.consultations[8]
        self.assertIsNone(consultation.parsed_date())
        self.assertFalse(date_redactor.is_redact(consultation))

    def test_is_redact_returns_false_if_parsed_date_is_on_start_date(self):
        date_redactor = DateRedactor(date(2018, 2, 1))
        consultation = self.consultations[0]
        self.assertIsInstance(consultation.parsed_date(), date)
        self.assertFalse(date_redactor.is_redact(consultation))

    def test_is_redact_returns_false_if_parsed_date_is_after_start_date(self):
        date_redactor = DateRedactor(date(2018, 1, 1))
        consultation = self.consultations[0]
        self.assertIsInstance(consultation.parsed_date(), date)
        self.assertFalse(date_redactor.is_redact(consultation))
