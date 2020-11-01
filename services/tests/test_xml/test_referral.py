from services.tests.xml_test_case import XMLTestCase

from services.xml.referral import Referral


class ReferralTest(XMLTestCase):
    def setUp(self):
        super().setUp(Referral.XPATH)
        self.referrals = [Referral(e) for e in self.elements]

    def test_string_representation(self):
        self.assertEqual('Referral', str(self.referrals[0]))

    def test_description(self):
        self.assertEqual(
            'Orthopaedic referral',
            self.referrals[0].description()
        )

    def test_date(self):
        self.assertEqual('07/11/2016', self.referrals[0].date())

    def test_provider_refid(self):
        self.assertEqual('5604', self.referrals[0].provider_refid())

    def test_xpaths(self):
        self.assertListEqual(
            [".//Referral[GUID='3487623']"],
            self.referrals[0].xpaths()
        )
