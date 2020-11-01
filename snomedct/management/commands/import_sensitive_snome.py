from django.core.management.base import BaseCommand
from django.conf import settings
from medicalreport.models import NhsSensitiveConditions
import os


class Command(BaseCommand):
    help = 'Import Sensitive snomed code data'

    def handle(self, *args, **options):
        self.stdout.write("clearing old sensitive data...")
        NhsSensitiveConditions.objects.all().delete()
        self.stdout.write("clearing success...")

        path = os.path.join(os.path.dirname(settings.BASE_DIR), 'initial_data/nhs_sensitive_conditions.txt')
        with open(path) as file:
            file_lines = file.readlines()
        self.stdout.write("starting import sensitive data...")
        for line in file_lines[1:]:
            NhsSensitiveConditions.objects.create(group=line.split()[0], snome_code=line.split()[1])
            self.stdout.write("imported subsetID: {subset_id}, snomedID: {snome_id}".format(
                subset_id=line.split()[0], snome_id=line.split()[1]
            ))
        self.stdout.write("import completed")
