import os
import gzip
from django.db import connection
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from import_export.formats import base_formats
from snomedct.models import SnomedConcept, SnomedDescendant, ReadCode
from django.core.files import File


class Command(BaseCommand):
    help = 'Import Snomed Concepts'
    csv_format = base_formats.CSV()
    data_file_path = os.path.join(settings.CONFIG_DIR, 'data/')
    temp_out_file = data_file_path + '/temp.csv'

    def truncate_table(self, model):
        self.stdout.write("trucating table {}...".format(model._meta.db_table))
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE {} CASCADE".format(model._meta.db_table))
        self.stdout.write("trucating table {} Done.".format(model._meta.db_table))

    def reset_sequence_serial(self, model):
        self.stdout.write("reset serail sequence on table {}...".format(model._meta.db_table))
        if not issubclass(model, SnomedConcept):
            with connection.cursor() as cursor:
                query = "SELECT setval(pg_get_serial_sequence('\"{tablename}\"','id'), coalesce(max(\"id\"), 1), max(\"id\") IS NOT null) FROM \"{tablename}\";".format(tablename=model._meta.db_table)
                cursor.execute(query)

        self.stdout.write("reset serail sequence on table {} Done.".format(model._meta.db_table))

    def delete_temp_file(self):
        if os.path.isfile(self.temp_out_file):
            os.remove(self.temp_out_file)

    def unzip_file(self, gzip_file_path):
        gzip_file = gzip.GzipFile(gzip_file_path, 'rb')
        gzip_datas = gzip_file.read()
        gzip_file.close()

        with open(self.temp_out_file, 'wb') as uncompressed_data:
            uncompressed_file = File(uncompressed_data)
            uncompressed_file.write(gzip_datas)

        return self.temp_out_file

    def import_into_portgres(self, model, input_file):
        self.stdout.write("importing data into {}...".format(model._meta.db_table))
        uncompressed_file = self.unzip_file(input_file)
        insert_count = model.objects.from_csv(uncompressed_file)
        self.stdout.write("{} records inserted".format(insert_count))
        self.delete_temp_file()
        self.stdout.write("importing data into {} Done.".format(model._meta.db_table))

    def import_data(self, model, input_file):
        self.truncate_table(model)
        self.reset_sequence_serial(model)
        self.import_into_portgres(model, input_file)

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--snomed_concepts',
            action='store_true',
            dest='snomed_concepts',
            help='Import data from snomed_concepts.csv.gz, snomed_descendants.csv.gz, readcodes.csv.gz files',
        )
        parser.add_argument(
            '--snomed_descendants',
            action='store_true',
            dest='snomed_descendants',
            help='Import data from snomed_descendants.csv.gz file',
        )
        parser.add_argument(
            '--readcodes',
            action='store_true',
            dest='readcodes',
            help='Import data from readcodes.csv.gz file',
        )

    def handle(self, *args, **options):
        if options['snomed_concepts']:
            self.import_data(SnomedConcept, self.data_file_path + 'snomed_concepts.csv.gz')
            self.import_data(SnomedDescendant, self.data_file_path + 'snomed_descendants.csv.gz')
            self.import_data(ReadCode, self.data_file_path + 'readcodes.csv.gz')
        if options['snomed_descendants']:
            self.import_data(SnomedDescendant, self.data_file_path + 'snomed_descendants.csv.gz')
        if options['readcodes']:
            self.import_data(ReadCode, self.data_file_path + 'readcodes.csv.gz')
