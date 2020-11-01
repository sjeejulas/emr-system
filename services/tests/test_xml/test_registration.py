from services.tests.xml_test_case import XMLTestCase
from services.xml.registration import Registration

from datetime import date


class RegistrationTest(XMLTestCase):
    def setUp(self):
        super().setUp(Registration.XPATH)
        self.registration = Registration(self.elements[0])

    def test_date_of_birth(self):
        self.assertEqual('01/04/1957', self.registration.date_of_birth())

    def test_parsed_date_of_birth(self):
        self.assertEqual(
            date(1957, 4, 1),
            self.registration.parsed_date_of_birth()
        )

    def test_sex(self):
        self.assertEqual('M', self.registration.sex())

    def test_full_name(self):
        self.assertEqual('Mr John Benson', self.registration.full_name())

    def test_nhs_number(self):
        self.assertEqual('5555555555', self.registration.nhs_number())

    def test_address_lines(self):
        self.assertListEqual(
            [
                '13 Victoria Street',
                'Four Lane Ends',
                'Ovenden',
                'West Yorkshire',
                'BD11 1AT'
            ],
            self.registration.address_lines()
        )

    def test_ref_id(self):
        self.assertEqual('2345', self.registration.ref_id())
