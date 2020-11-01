from services.tests.xml_test_case import XMLTestCase

from services.xml.value_event import ValueEvent, load_bloods_data

BLOOD_DATA_FILEPATH = 'services/tests/test_data/bloods.yml'


class ValueEventTest(XMLTestCase):
    def setUp(self):
        super().setUp(ValueEvent.XPATH)
        self.value_events = [ValueEvent(e) for e in self.elements]

    def test_string_representation(self):
        for ve in self.value_events:
            self.assertEqual('ValueEvent', str(ve))

    def test_date(self):
        self.assertEqual('05/05/2015', self.value_events[0].date())

    def test_description(self):
        self.assertEqual(
            '123 mmHg',
            self.value_events[0].description())

    def test_has_bmi(self):
        self.assertFalse(self.value_events[0].has_bmi())
        self.assertTrue(self.value_events[11].has_bmi())

    def test_has_weight(self):
        self.assertFalse(self.value_events[0].has_weight())
        self.assertTrue(self.value_events[10].has_weight())

    def test_has_height(self):
        self.assertFalse(self.value_events[0].has_height())
        self.assertTrue(self.value_events[9].has_height())

    def test_has_systolic_blood_pressure(self):
        self.assertFalse(self.value_events[0].has_systolic_blood_pressure())
        self.assertTrue(self.value_events[1].has_systolic_blood_pressure())

    def test_has_diastolic_blood_pressure(self):
        self.assertFalse(self.value_events[1].has_diastolic_blood_pressure())
        self.assertTrue(self.value_events[0].has_diastolic_blood_pressure())

    def test_has_blood_test_returns_false_when_no_match(self):
        self.assertFalse(self.value_events[2].has_blood_test('hemoglobin'))

    def test_has_blood_test_from_snomed(self):
        self.assertTrue(self.value_events[4].has_blood_test('hemoglobin'))

    def test_has_blood_test_from_readcode(self):
        self.assertTrue(
            self.value_events[2].has_blood_test('white_blood_count')
        )

    def test_blood_test_types(self):
        self.assertCountEqual(
            [
                'white_blood_count', 'hemoglobin', 'platelets',
                'mean_cell_volume', 'mean_corpuscular_hemoglobin',
                'neutrophils', 'lymphocytes', 'sodium', 'potassium', 'urea',
                'creatinine', 'c_reactive_protein', 'bilirubin',
                'alkaline_phosphatase', 'alanine_aminotransferase',
                'albumin', 'gamma_gt', 'triglycerides', 'total_cholesterol',
                'high_density_lipoprotein', 'low_density_lipoprotein',
                'random_glucose', 'fasting_glucose', 'hba1c'
            ],
            ValueEvent.blood_test_types()
        )


class LoadBloodsDataTest(XMLTestCase):
    def test_load_bloods_data(self):
        self.assertIsInstance(load_bloods_data(BLOOD_DATA_FILEPATH), dict)
