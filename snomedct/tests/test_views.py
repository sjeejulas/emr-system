from django.test import TestCase
from django.shortcuts import reverse

from snomedct.views import get_descendants, query_snomed
from snomedct.models import SnomedConcept, SnomedDescendant
from snomedct.tests.test_models import ConceptCodeTestCase

from model_mommy import mommy

import json


class GetSnomeApiTest(ConceptCodeTestCase):

    def setUp(self):
        super().setUp()
        self.snomedct_41 = mommy.make(SnomedConcept, fsn_description='test description(disorder)')

    def test_call_query_snomed(self):
        response = self.client.get(reverse('snomedct:query_snomed'), {'keyword': self.snomedct_41.fsn_description})

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            str(response.content, encoding='utf-8'),
            [
                {
                    "id": self.snomedct_41.external_id,
                    "text": self.snomedct_41.fsn_description,
                }
            ]
        )

    def test_call_get_descendants(self):
        response = self.client.get(reverse('snomedct:get_descendants'), {'snomedct': self.snomedct_0.pk})

        self.assertEqual(response.status_code, 200)

        response_list = json.loads(str(response.content, encoding='utf-8'))
        response_external_ids = []
        for d in response_list:
            response_external_ids.append(d['external_id'])
        sorted_response_external_ids = sorted(response_external_ids)
        sorted_expected_result = sorted([
            self.snomedct_0.external_id,
            self.snomedct_11.external_id,
            self.snomedct_12.external_id,
            self.snomedct_21.external_id,
            self.snomedct_22.external_id,
            self.snomedct_23.external_id,
            self.snomedct_24.external_id,
            self.snomedct_31.external_id,
            self.snomedct_32.external_id,
        ])
        self.assertEqual(sorted_response_external_ids, sorted_expected_result)


class GetReadCodeApiTest(ConceptCodeTestCase):

    def setUp(self):
        super().setUp()

    def test_call_get_readcodes(self):
        response = self.client.get(reverse('snomedct:get_readcodes'), {'snomedct': self.snomedct_0.pk})

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            str(response.content, encoding='utf-8'),
            [
                {
                    "id": self.readcode_0.id,
                    "ext_read_code": self.readcode_0.ext_read_code,
                    "fsn_description": self.readcode_0.concept_id.fsn_description,
                    "external_id": self.readcode_0.concept_id.external_id
                },
            ]
        )

    def test_call_get_descendant_readcodes(self):
        response = self.client.get(reverse('snomedct:get_descendant_readcodes'), {'snomedct': self.snomedct_0.pk})
        expected = [
                {
                    "id": self.readcode_0.id,
                    "ext_read_code": self.readcode_0.ext_read_code,
                    "fsn_description": self.readcode_0.concept_id.fsn_description,
                    "external_id": self.readcode_0.concept_id.external_id
                },
                {
                    "id": self.readcode_11.id,
                    "ext_read_code": self.readcode_11.ext_read_code,
                    "fsn_description": self.readcode_11.concept_id.fsn_description,
                    "external_id": self.readcode_11.concept_id.external_id
                },
                {
                    "id": self.readcode_12.id,
                    "ext_read_code": self.readcode_12.ext_read_code,
                    "fsn_description": self.readcode_12.concept_id.fsn_description,
                    "external_id": self.readcode_12.concept_id.external_id
                },
                {
                    "id": self.readcode_21.id,
                    "ext_read_code": self.readcode_21.ext_read_code,
                    "fsn_description": self.readcode_21.concept_id.fsn_description,
                    "external_id": self.readcode_21.concept_id.external_id
                },
                {
                    "id": self.readcode_22.id,
                    "ext_read_code": self.readcode_22.ext_read_code,
                    "fsn_description": self.readcode_22.concept_id.fsn_description,
                    "external_id": self.readcode_22.concept_id.external_id
                },
                {
                    "id": self.readcode_23.id,
                    "ext_read_code": self.readcode_23.ext_read_code,
                    "fsn_description": self.readcode_23.concept_id.fsn_description,
                    "external_id": self.readcode_23.concept_id.external_id
                },
                {
                    "id": self.readcode_24.id,
                    "ext_read_code": self.readcode_24.ext_read_code,
                    "fsn_description": self.readcode_24.concept_id.fsn_description,
                    "external_id": self.readcode_24.concept_id.external_id
                },
                {
                    "id": self.readcode_31.id,
                    "ext_read_code": self.readcode_31.ext_read_code,
                    "fsn_description": self.readcode_31.concept_id.fsn_description,
                    "external_id": self.readcode_31.concept_id.external_id
                },
                {
                    "id": self.readcode_32.id,
                    "ext_read_code": self.readcode_32.ext_read_code,
                    "fsn_description": self.readcode_32.concept_id.fsn_description,
                    "external_id": self.readcode_32.concept_id.external_id
                },
            ]
        self.assertEqual(response.status_code, 200)

        self.assertListEqual(
            sorted(json.loads(response.content), key=lambda k: k['id']),
            sorted(expected, key=lambda k: k['id'])
        )

