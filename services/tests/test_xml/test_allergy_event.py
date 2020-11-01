from services.tests.xml_test_case import XMLTestCase
from services.xml.allergy_event import AllergyEvent


class AllergyEventTest(XMLTestCase):
    def setUp(self):
        super().setUp(AllergyEvent.XPATH)
        self.allergy_events = [AllergyEvent(e) for e in self.elements]

    def test_description(self):
        self.assertEqual(
            'H/O: penicillin allergy',
            self.allergy_events[0].description()
        )
