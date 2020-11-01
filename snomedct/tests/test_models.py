from django.test import TestCase, tag
from model_mommy import mommy

from snomedct.models import (
    SnomedConcept, ReadCode, SnomedDescendant, CommonSnomedConcepts
)


class ConceptCodeTestCase(TestCase):
    def setUp(self):
        self.snomedct_0 = mommy.make(SnomedConcept)
        self.snomedct_11 = mommy.make(SnomedConcept)
        self.snomedct_12 = mommy.make(SnomedConcept)
        self.snomedct_21 = mommy.make(SnomedConcept)
        self.snomedct_22 = mommy.make(SnomedConcept)
        self.snomedct_23 = mommy.make(SnomedConcept)
        self.snomedct_24 = mommy.make(SnomedConcept)
        self.snomedct_31 = mommy.make(SnomedConcept)
        self.snomedct_32 = mommy.make(SnomedConcept)
        self.readcode_0 = mommy.make(ReadCode, concept_id=self.snomedct_0)
        self.readcode_11 = mommy.make(ReadCode, concept_id=self.snomedct_11)
        self.readcode_12 = mommy.make(ReadCode, concept_id=self.snomedct_12)
        self.readcode_21 = mommy.make(ReadCode, concept_id=self.snomedct_21)
        self.readcode_22 = mommy.make(ReadCode, concept_id=self.snomedct_22)
        self.readcode_23 = mommy.make(ReadCode, concept_id=self.snomedct_23)
        self.readcode_24 = mommy.make(ReadCode, concept_id=self.snomedct_24)
        self.readcode_31 = mommy.make(ReadCode, concept_id=self.snomedct_31)
        self.readcode_32 = mommy.make(ReadCode, concept_id=self.snomedct_32)

        mommy.make(
            SnomedDescendant,
            external_id=self.snomedct_0,
            descendant_external_id=self.snomedct_11)
        mommy.make(
            SnomedDescendant,
            external_id=self.snomedct_0,
            descendant_external_id=self.snomedct_12)
        mommy.make(
            SnomedDescendant,
            external_id=self.snomedct_11,
            descendant_external_id=self.snomedct_21)
        mommy.make(
            SnomedDescendant,
            external_id=self.snomedct_11,
            descendant_external_id=self.snomedct_22)
        mommy.make(
            SnomedDescendant,
            external_id=self.snomedct_12,
            descendant_external_id=self.snomedct_22)
        mommy.make(
            SnomedDescendant,
            external_id=self.snomedct_12,
            descendant_external_id=self.snomedct_23)
        mommy.make(
            SnomedDescendant,
            external_id=self.snomedct_12,
            descendant_external_id=self.snomedct_24)
        mommy.make(
            SnomedDescendant,
            external_id=self.snomedct_22,
            descendant_external_id=self.snomedct_31)
        mommy.make(
            SnomedDescendant,
            external_id=self.snomedct_23,
            descendant_external_id=self.snomedct_31)
        mommy.make(
            SnomedDescendant,
            external_id=self.snomedct_23,
            descendant_external_id=self.snomedct_32)


class SnomedConceptTest(ConceptCodeTestCase):
    def setUp(self):
        super().setUp()
        self.snomedct = mommy.make(
            SnomedConcept, fsn_description='fsn_description',
            external_id=1234567890
        )
        self.snomed_descendant_1 = mommy.make(
            SnomedDescendant, descendant_external_id=self.snomedct
        )
        self.snomed_descendant_2 = mommy.make(SnomedDescendant)

    def test_string_representation(self):
        self.assertEqual(
            str(self.snomedct),
            f'{self.snomedct.pk} - fsn_description'
        )

    def test_descendant_readcodes(self):
        self.assertCountEqual(
            [
                self.readcode_0, self.readcode_11, self.readcode_12,
                self.readcode_21, self.readcode_22, self.readcode_23,
                self.readcode_24, self.readcode_31, self.readcode_32
            ],
            self.snomedct_0.descendant_readcodes()
        )

    def test_children_relationship_is_modelled_correctly(self):
        self.assertCountEqual(
            [self.snomedct_11, self.snomedct_12],
            self.snomedct_0.children.all()
        )
        self.assertCountEqual(
            [self.snomedct_21, self.snomedct_22],
            self.snomedct_11.children.all()
        )
        self.assertCountEqual(
            [self.snomedct_22, self.snomedct_23, self.snomedct_24],
            self.snomedct_12.children.all()
        )
        self.assertCountEqual([], self.snomedct_21.children.all())
        self.assertCountEqual(
            [self.snomedct_31, self.snomedct_32],
            self.snomedct_23.children.all()
        )

    def test_descendants_with_include_self(self):
        self.assertCountEqual(
            [
                self.snomedct_0, self.snomedct_11, self.snomedct_12,
                self.snomedct_21, self.snomedct_22, self.snomedct_23,
                self.snomedct_24, self.snomedct_31, self.snomedct_32
            ],
            self.snomedct_0.descendants(ret_descendants=set())
        )

    def test_descendants_without_include_self(self):
        self.assertCountEqual(
            [
                self.snomedct_11, self.snomedct_12,
                self.snomedct_21, self.snomedct_22, self.snomedct_23,
                self.snomedct_24, self.snomedct_31, self.snomedct_32
            ],
            self.snomedct_0.descendants(include_self=False, ret_descendants=set())
        )

    def test_is_descendant_of(self):
        valid_pairs = [
            (self.snomedct_0, self.snomedct_0),
            (self.snomedct_12, self.snomedct_0),
            (self.snomedct_31, self.snomedct_0),
            (self.snomedct_32, self.snomedct_12)
        ]
        invalid_pairs = [
            (self.snomedct_32, self.snomedct_11),
            (self.snomedct_0, self.snomedct_11),
            (self.snomedct_24, self.snomedct_22)
        ]
        for vp in valid_pairs:
            self.assertTrue(vp[0].is_descendant_of(vp[1]))
        for ivp in invalid_pairs:
            self.assertFalse(ivp[0].is_descendant_of(ivp[1]))


class ReadCodeTest(ConceptCodeTestCase):
    def setUp(self):
        super().setUp()
        self.readcode = mommy.make(ReadCode, ext_read_code='12345')

    def test_string_representation(self):
        self.assertEqual(
            str(self.readcode), f'{self.readcode.pk} - 12345'
        )

    def test_is_descendant_of_snomed_concept(self):
        valid_pairs = [
            (self.readcode_0, self.snomedct_0),
            (self.readcode_12, self.snomedct_0),
            (self.readcode_31, self.snomedct_0),
            (self.readcode_32, self.snomedct_12)
        ]
        invalid_pairs = [
            (self.readcode_32, self.snomedct_11),
            (self.readcode_0, self.snomedct_11),
            (self.readcode_24, self.snomedct_22)
        ]
        for vp in valid_pairs:
            self.assertTrue(vp[0].is_descendant_of_snomed_concept(vp[1]))
        for ivp in invalid_pairs:
            self.assertFalse(ivp[0].is_descendant_of_snomed_concept(ivp[1]))

    def test_related_snomed_concepts_and_descendants(self):
        self.readcode_11.concept_id = self.snomedct_12
        self.readcode_11.save()
        self.assertCountEqual(
            set([
                self.snomedct_31, self.snomedct_32, self.snomedct_22,
                self.snomedct_12, self.snomedct_23,self.snomedct_24,
            ]),
            self.readcode_11.related_snomed_concepts_and_descendants()
        )


class SnomedDescendantTest(TestCase):
    def setUp(self):
        self.snomedct = mommy.make(SnomedConcept, fsn_description='fsn_description')
        self.snomed_descendant = mommy.make(
            SnomedDescendant, descendant_external_id=self.snomedct,
            external_id=self.snomedct
        )

    def test_string_representation(self):
        self.assertEqual(
            str(self.snomed_descendant),
            f'{self.snomed_descendant.pk} - fsn_description - {self.snomedct.pk} - fsn_description'
        )


class CommonSnomedConceptsTest(TestCase):
    def setUp(self):
        self.snomedct = mommy.make(
            SnomedConcept, fsn_description='fsn_description',
            external_id=1234567890
        )
        self.common_snomed_concepts = mommy.make(
            CommonSnomedConcepts, common_name='Heart Disease', snomed_concept_code=[self.snomedct]
        )

    def test_string_representation(self):
        self.assertEqual(
            str(self.common_snomed_concepts), 'Heart Disease'
        )
