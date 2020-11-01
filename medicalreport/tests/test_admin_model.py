
from django.test import TestCase

from django.contrib.admin.sites import AdminSite
from django.contrib.admin.options import ModelAdmin

from medicalreport.models import ReferencePhrases
from medicalreport.admin import ReferencePhrasesAdmin


class ReferencePhraseAdminTests(TestCase):
    def setUp(self):
        self.referphrase = ReferencePhrases.objects.create(name='father')
        self.site = AdminSite()

    def test_referencephraseadmin_str(self):
        ref_phrase = ModelAdmin(ReferencePhrases, self.site)
        self.assertEqual(str(ref_phrase), 'medicalreport.ModelAdmin')