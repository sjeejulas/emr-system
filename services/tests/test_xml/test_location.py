from services.tests.xml_test_case import XMLTestCase

from services.xml.location import Location


class LocationTest(XMLTestCase):
    def setUp(self):
        super().setUp(Location.XPATH)
        self.locations = [Location(e) for e in self.elements]

    def test_address_lines(self):
        self.assertListEqual(
            [
                'Main Branch',
                'Fulford Grange, Micklefield Lane',
                'Rawdon',
                'Rawdon',
                'Leeds',
                'Yorkshire',
                'LS19 6BA'
            ],
            self.locations[0].address_lines()
        )

    def test_location_name(self):
        self.assertEqual('Main Branch', self.locations[0].location_name())

    def test_ref_id(self):
        self.assertEqual('2670', self.locations[0].ref_id())
