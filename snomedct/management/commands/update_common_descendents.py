from django.core.management.base import BaseCommand
from django.conf import settings
from snomedct.models import CommonSnomedConcepts, SnomedConcept
import os


class Command(BaseCommand):
    help = 'Update descendant ids of common snomed concept'

    def handle(self, *args, **options):
        common_snome_list = CommonSnomedConcepts.objects.all()
        for common in common_snome_list:
            self.stdout.write('-'*100)
            self.stdout.write(common.common_name)
            self.stdout.write('updating...')
            descendants_snome_codes = []
            descendants_readcodes = []
            for snomed in common.snomed_concept_code.all():
                snomed_descendants = snomed.descendants(ret_descendants=set())
                descendants_snome_codes.extend([descendant.pk for descendant in snomed_descendants])
                descendants_readcodes.extend([read_code.ext_read_code for read_code in snomed.descendant_readcodes(snomed_descendants)])
            common.descendant_snomed_id = list(set(descendants_snome_codes))
            common.descendant_readcodes = list(set(descendants_readcodes))
            common.save()
            self.stdout.write("completed".format(common_name=common.common_name))
