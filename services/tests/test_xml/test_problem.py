from services.tests.xml_test_case import XMLTestCase
from services.xml.problem import Problem

from datetime import date


class ProblemTest(XMLTestCase):
    def setUp(self):
        super().setUp(Problem.XPATH)
        self.problems = [Problem(p) for p in self.elements]
        """
            Display term on each problems
                problems[0] is Asthma
                problems[1] is Gout
                problems[2] is Coughing
                problems[3] is O/E - weight, 15 kg
        """

    def test_is_active_returns_true_when_active(self):
        self.assertTrue(self.problems[0].is_active())

    def test_is_active_returns_false_when_not_active(self):
        self.assertFalse(self.problems[1].is_active())

    def test_is_active_returns_none_when_status_unknown(self):
        self.assertIsNone(self.problems[2].is_active())

    def test_is_past_returns_true_when_not_active(self):
        self.assertTrue(self.problems[1].is_past())

    def test_is_past_returns_false_when_active(self):
        self.assertFalse(self.problems[0].is_past())

    def test_is_past_returns_none_when_status_unknown(self):
        self.assertIsNone(self.problems[2].is_past())

    def test_is_significant_returns_true_when_significant(self):
        self.assertTrue(self.problems[0].is_significant())

    def test_is_significant_returns_false_when_not_significant(self):
        self.assertFalse(self.problems[3].is_significant())

    def test_is_significant_returns_none_when_status_unknown(self):
        self.assertIsNone(self.problems[2].is_significant())

    def test_is_minor_returns_true_when_minor(self):
        self.assertTrue(self.problems[3].is_minor())

    def test_is_minor_returns_false_when_not_minor(self):
        self.assertFalse(self.problems[1].is_minor())

    def test_is_minor_returns_none_when_status_unknown(self):
        self.assertIsNone(self.problems[2].is_minor())

    def test_date(self):
        self.assertEqual('05/05/2015', self.problems[3].date())

    def test_end_date(self):
        self.assertEqual('06/09/2014', self.problems[2].end_date())

    def test_parsed_end_date(self):
        self.assertEqual(
            date(2014, 9, 6),
            self.problems[2].parsed_end_date()
        )

    def test_description(self):
        self.assertEqual('Asthma', self.problems[0].description())

    def test_xpaths(self):
        self.assertCountEqual(
            [".//Event[GUID='98764']"],
            self.problems[0].xpaths()
        )
