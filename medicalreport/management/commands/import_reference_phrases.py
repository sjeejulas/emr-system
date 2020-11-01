from django.core.management.base import BaseCommand
from django.conf import settings
from medicalreport.models import ReferencePhrases
import os


class Command(BaseCommand):
    help = 'Import name and relationships data'

    def handle(self, *args, **options):
        self.stdout.write("clearing old data...")
        ReferencePhrases.objects.all().delete()
        self.stdout.write("clearing success...")
        path = os.path.join(os.path.dirname(settings.BASE_DIR), 'initial_data/reference_phrases.csv')
        self.stdout.write("starting import sensitive data...")
        ReferencePhrases.objects.from_csv(path)
        self.stdout.write("import completed")
