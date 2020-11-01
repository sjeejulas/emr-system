from django.core.management.base import BaseCommand
from django.conf import settings
from medicalreport.models import ReferencePhrases
from payment.cron.genarate_invoice import genarated_weekly_invoice
import os


class Command(BaseCommand):
    help = 'Genarate weekly invoice data.'

    def handle(self, *args, **options):
        genarated_weekly_invoice()
        self.stdout.write("Genarate weekly completed !")
