import os

from celery import Celery

if os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.environ.get('DJANGO_SETTINGS_MODULE'))
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medi.settings.prod_settings')

os.environ.setdefault('AES_KEY', 'Sn1LmZKUcvjBLE2WDMNsRVdegW981PQ4')
os.environ.setdefault('SENDGRID_USER', 'medi2data')
os.environ.setdefault('SENDGRID_PASS', 'medimemo1234')
app = Celery('medi')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
