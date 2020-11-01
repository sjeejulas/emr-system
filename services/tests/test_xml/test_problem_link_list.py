from services.tests.xml_test_case import XMLTestCase

from services.xml.problem_link_list import ProblemLinkList


class ProblemLinkListTest(XMLTestCase):
    def setUp(self):
        super().setUp(ProblemLinkList.XPATH)
        self.problem_link_list = ProblemLinkList(self.elements[0])

    def test_target_guids(self):
        self.assertListEqual(['23423'], self.problem_link_list.target_guids())

    def test_date(self):
        self.assertEqual('07/11/2016', self.problem_link_list.date())

    def test_xpaths(self):
        self.assertListEqual(
            [".//Event[GUID='{32DD97D5-EFF6-4ACF-9E65-F7A40C8F469B}']"],
            self.problem_link_list.xpaths()
        )
