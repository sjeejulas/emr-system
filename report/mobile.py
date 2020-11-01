import json
import requests
from django.conf import settings


class AuthMobile:
    def __init__(self, **kwargs):
        self.url = "https://api.checkmobi.com/v1/validation/"
        self.header = {
            "Authorization": settings.CHECKMOBI_SECRET_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.number = kwargs.get('number')
        self.mobi_id = kwargs.get('mobi_id')
        self.pin = kwargs.get('pin')
        self.type = kwargs.get('type', 'sms')
        self.language = kwargs.get('language', 'en-GB')

    def request(self):
        data = json.dumps({"number": self.number, "type": self.type, "language": self.language, "platform": "web"})
        response = requests.post(self.url + "request", data, headers=self.header)
        return response

    def verify(self):
        data = json.dumps({"id": self.mobi_id, "pin": self.pin})
        response = requests.post(self.url + "verify", data, headers=self.header)
        return response


class SendSMS:
    def __init__(self, **kwargs):
        self.url = "https://api.checkmobi.com/v1/sms/"
        self.header = {
            "Authorization": settings.CHECKMOBI_SECRET_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.number = kwargs.get('number')

    def send(self, msg: str):
        data = json.dumps({"to": self.number, "text": msg, "platform":"web"})
        response = requests.post(self.url + "send", data, headers=self.header)
        return response
