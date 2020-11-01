from services.tests.xml_test_case import XMLTestCase

from services.xml.person import Person


class PersonTest(XMLTestCase):
    def setUp(self):
        super().setUp(Person.XPATH)
        self.persons = [Person(e) for e in self.elements]

    def test_full_name(self):
        self.assertEqual(
            'Blue Bay (General Medical Practitioner)',
            self.persons[0].full_name()
        )

    def test_category_description(self):
        self.assertEqual(
            'General Medical Practitioner',
            self.persons[0].category_description()
        )

    def test_name(self):
        self.assertEqual('Blue Bay', self.persons[0].name())

    def test_ref_id(self):
        self.assertEqual('2670', self.persons[0].ref_id())
