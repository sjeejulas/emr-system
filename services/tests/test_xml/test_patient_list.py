from services.tests.xml_test_case import XMLTestCase

from services.xml.patient_list import PatientList
from services.xml.registration import Registration


class PatientListTest(XMLTestCase):
    def setUp(self):
        super().setUp()
        self.patient_list = PatientList(self.parsed_xml)

    def test_patients(self):
        patients = self.patient_list.patients()
        self.assertEqual(1, len(patients))
        self.assertIsInstance(patients[0], Registration)
