from django.utils import timezone
from django.db.models import Q
from instructions.models import Instruction
from instructions.model_choices import INSTRUCTION_STATUS_COMPLETE
from datetime import timedelta
import datetime
from payment.model_choices import *
from payment.models import *
from payment.functions import PaymentInvoice
from organisations.models import OrganisationClient
from organisations.models import OrganisationMedidata
from django.conf import settings
import uuid


def genarated_weekly_invoice():
    total_cost = 0
    now = timezone.now()
    client_org = OrganisationClient.objects.all()
    invoice_data = list()
    for client in client_org:
        weekly_table = WeeklyInvoice()
        weekly_table.start_date = now - datetime.timedelta(days=7)
        weekly_table.end_date = now
        weekly_table.client_org = client
        weekly_table.save()
        complete_instructions = Instruction.objects.filter(
            status=INSTRUCTION_STATUS_COMPLETE,
            client_user__organisation=client
        )
        for instruction in complete_instructions:
            dute_date = now - instruction.completed_signed_off_timestamp
            if dute_date == 7:
                instruction.invoice_in_week = weekly_table
                instruction.save()

                gp_earn = instruction.gp_earns
                medi_earn = instruction.medi_earns
                total_cost = total_cost + gp_earn + medi_earn

                invoice_data.append(instruction)

        medi_user = OrganisationMedidata.objects.first()
        date_detail = {
            'date_invoice': now,
            'dute_date': now + timedelta(days=7)
        }
        params = {
            'client_detail': client,
            'medi_detail': medi_user,
            'date_detail': date_detail,
            'record': invoice_data
        }

        uuid_hex = uuid.uuid4().hex
        weekly_table.weekly_invoice_pdf_file.save('invoice_%s.pdf'%uuid_hex, PaymentInvoice.get_invoice_pdf_file(params))

        weekly_table.total_cost = total_cost
        weekly_table.number_instructions = len(invoice_data)
        weekly_table.paid = False
        weekly_table.save()
