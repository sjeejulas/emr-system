from .common import *

ALLOWED_HOSTS.append('medi.mohub.co')
ALLOWED_HOSTS.append('web02-cl02-mde.flexiion-customer.net')

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'medi',
        'USER': 'medi',
        'PASSWORD': 'medi',
        'HOST': 'db',
        'PORT': '5432',
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(levelname)s: %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'medi_info.log',
            'when': 'w0',
            'interval': 1,
            'backupCount': 10,
            'formatter': 'simple'
        }
    },
    'loggers': {
        'raven': {
            'level': 'ERROR',
            'handlers': ['sentry','console'],
            'propagate': False,
        },
        'django.request': {
            'level': 'ERROR',
            'handlers': ['sentry','console'],
            'propagate': False,
        },
        'medidata.event': {
            'level': 'INFO',
            'handlers': ['file',],
        }
    }
}

EMIS_API_HOST = 'http://medi2data.net:9443'

MDX_URL = 'http://medi.mohub.co'
EMR_URL = 'http://medi.mohub.co'

TWO_FACTOR_ENABLED=False
CELERY_ENABLED=False
CLAMD_ENABLED= False
