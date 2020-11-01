import datetime

from services.xml.xml_base import XMLModelBase

from datetime import date


class DateRedactor:
    def __init__(self, start_date=None, from_date=None, to_date=None):
        self.start_date = start_date
        self.from_date = from_date.date() if isinstance(from_date, datetime.datetime) else from_date
        self.to_date = to_date.date() if isinstance(to_date, datetime.datetime) else to_date

    def is_redact(self, model: XMLModelBase) -> bool:
        parsed_date = model.parsed_date()

        if parsed_date and not self.from_date and not self.to_date:
            return not(self.case_start_date(parsed_date))
        elif parsed_date and (self.from_date and self.to_date):
            return not(self.case_date_range(parsed_date) and self.case_start_date(parsed_date))
        else:
            return not(self.case_date_range(parsed_date))

    def case_date_range(self, parsed_date):
        flag = True
        if self.from_date and parsed_date and parsed_date < self.from_date:
            flag = False
        if self.to_date and parsed_date and parsed_date > self.to_date:
            flag = False
        return flag

    def case_start_date(self, parsed_date) -> bool:
        if self.start_date and parsed_date < self.start_date:
            return False
        return True
