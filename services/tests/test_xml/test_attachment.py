from services.tests.xml_test_case import XMLTestCase
from services.xml.attachment import Attachment


class AttachmentTest(XMLTestCase):
    def setUp(self):
        super().setUp(Attachment.XPATH)
        self.attachments = [Attachment(e) for e in self.elements]

    def test_string_representation(self):
        for a in self.attachments:
            self.assertEqual('Attachment', str(a))

    def test_description(self):
        self.assertEqual(
            'Clinical letter RE asthma diagnosis',
            self.attachments[0].description()
        )

    def test_dds_identifier(self):
        self.assertEqual('DDS080', self.attachments[2].dds_identifier())

    def test_to_param(self):
        self.assertEqual('DDS080', self.attachments[2].to_param())

    def test_xpaths(self):
        self.assertListEqual(
            [".//Attachment[GUID='387678']"],
            self.attachments[0].xpaths()
        )
