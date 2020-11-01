from django.test import Client, RequestFactory
from django.utils import timezone
from model_mommy import mommy

from accounts.models import User
from instructions.models import Instruction
from payment.tests.test_functions import CalculateInstructionFeeBaseTest
from payment.functions import calculate_instruction_fee
from instructions import model_choices
from payment.model_choices import FEE_CLAIMS_TYPE, FEE_SARS_TYPE

import csv
import io
import zipfile
import os
import re


class ImportExportTest(CalculateInstructionFeeBaseTest):

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.medidata_user = User.objects.create_superuser(email='medidta@test.com', password='test1234')
        self.client = Client()
        request = self.factory.get('/login/')
        self.client.login(request=request, email=self.medidata_user.email, password='test1234')
        self.amra_instruction = mommy.make(
            Instruction,
            id=3,
            type=model_choices.AMRA_TYPE,
            gp_practice=self.gp_practice,
            client_user=self.client_user,
            status=model_choices.INSTRUCTION_STATUS_COMPLETE,
            created=timezone.now(),
            completed_signed_off_timestamp=timezone.now(),
            type_catagory=FEE_CLAIMS_TYPE
        )
        self.sars_instruction = mommy.make(
            Instruction,
            id=4,
            type=model_choices.SARS_TYPE,
            gp_practice=self.gp_practice,
            client_user=self.client_user,
            status=model_choices.INSTRUCTION_STATUS_COMPLETE,
            created=timezone.now(),
            completed_signed_off_timestamp=timezone.now(),
            type_catagory=FEE_SARS_TYPE
        )
        self.instruction_status_header = 'ID, MediRef, Surgery, Status'
        self.instruction_content = [
            str(self.amra_instruction.id) + ', 10000003, Test Name GP Organisation, Completed',
            str(self.sars_instruction.id) + ', 10000004, Test Name GP Organisation, Completed'
        ]

        for instruction in Instruction.objects.all():
            calculate_instruction_fee(instruction)

    def test_export_payment_as_csv(self):
        response = self.client.post('/admin/instructions/instruction/', {'action': 'export_payment_as_csv'})
        self.assertEqual(response.status_code, 200)

        # load and extract members in zip file then keep temporary csv files to '/common/tests/test_file_data' directory
        z = zipfile.ZipFile(io.BytesIO(response.content))
        test_data_directory_path = os.getcwd()+'/common/tests/test_file_data'
        z.extractall(test_data_directory_path)

        # test contents of instruction status csv file
        instruction_status_file_name = z.filelist[1].filename
        instruction_reader = csv.reader(open(test_data_directory_path + '/' + instruction_status_file_name))

        for i, row in enumerate(instruction_reader):
            if i == 0:
                self.assertEqual(', '.join(row), self.instruction_status_header)
            else:
                self.assertEqual(', '.join(row), self.instruction_content[i-1])

        # test contents of payment report csv file
        payment_filename = z.filelist[0].filename
        payment_reader = csv.reader(open(test_data_directory_path + '/' + payment_filename))
        payment_header = 'Sort Code, Account number, GP Surgery, Amount, VAT, Reference'
        payment_content = [
            '12-34-56, 12345678, Test Name GP Organisation, 70.00, , '
        ]
        for i, row in enumerate(payment_reader):
            if i == 0:
                self.assertEqual(', '.join(row), payment_header)
            else:
                self.assertEqual(', '.join(row), payment_content[i-1])

        os.remove(test_data_directory_path + '/' + instruction_status_file_name)
        os.remove(test_data_directory_path + '/' + payment_filename)

    def test_export_client_payment_as_csv(self):
        response = self.client.post('/admin/instructions/instruction/', {'action': 'export_client_payment_as_csv'})
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        client_payment_reader = csv.reader(io.StringIO(content))
        body = list(client_payment_reader)
        client_payment_header = 'Client Id, Client Organisation, Amount, VAT, Reference'
        client_payment_content = [
            str(self.client_organisation.id) + ', Test Trading Name Client Organisation, 110.00, 8.00, '
        ]
        for i, row in enumerate(body):
            if i == 0:
                self.assertEqual(', '.join(row), client_payment_header)
            else:
                self.assertEqual(', '.join(row), client_payment_content[i-1])

    def test_export_status_report_as_csv(self):
        response = self.client.post(
            '/admin/instructions/instruction/',
            {
                'action': 'export_status_report_as_csv',
                '_selected_action': ['3', '4']
            }
        )
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        instruction_reader = csv.reader(io.StringIO(content))
        body = list(instruction_reader)
        for i, row in enumerate(body):
            if i == 0:
                self.assertEqual(', '.join(row), self.instruction_status_header)
            else:
                self.assertEqual(', '.join(row), self.instruction_content[i-1])

    def test_import_csv_for_update_paid_instruction_status(self):
        with open(os.getcwd() + '/common/tests/test_file_data/test_import_instruction_status.csv') as fp:
            response_preview_import = self.client.post(
                '/admin/instructions/instruction/import/', {'import_file': fp, 'input_format': '0'}
            )
            self.assertEqual(response_preview_import.status_code, 200)

            html_content = response_preview_import.content.decode('utf-8')
            import_file_name = re.search('name="import_file_name" value="(.+?)"', html_content).group(1)

            # before update status
            instruction_status_3 = Instruction.objects.get(id=3).status
            instruction_status_4 = Instruction.objects.get(id=4).status
            self.assertEqual(instruction_status_3, model_choices.INSTRUCTION_STATUS_COMPLETE)
            self.assertEqual(instruction_status_4, model_choices.INSTRUCTION_STATUS_COMPLETE)

            response_submit_import = self.client.post(
                '/admin/instructions/instruction/process_import/', {
                    'import_file_name': import_file_name,
                    'original_file_name': 'test_import_instruction_status.cs',
                    'input_format': '0'
                }
            )
            # success import will redirect to change list django admin
            self.assertEqual(response_submit_import.status_code, 302)

            # after update status
            instruction_status_3 = Instruction.objects.get(id=3).status
            instruction_status_4 = Instruction.objects.get(id=4).status
            self.assertEqual(instruction_status_3, model_choices.INSTRUCTION_STATUS_PAID)
            self.assertEqual(instruction_status_4, model_choices.INSTRUCTION_STATUS_PAID)
