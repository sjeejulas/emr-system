from services.tests.xml_test_case import XMLTestCase

from services.xml.referral_event import ReferralEvent


class ReferralEventTest(XMLTestCase):
    def setUp(self):
        super().setUp(ReferralEvent.XPATH)
        self.referral_event = ReferralEvent(self.elements[0])

    def test_date(self):
        self.assertEqual('06/02/2018', self.referral_event.date())

    def test_description(self):
        self.assertEqual(
            'Referral to specialist',
            self.referral_event.description()
        )

    def test_provider_refid_always_returns_none(self):
        self.assertIsNone(self.referral_event.provider_refid())
