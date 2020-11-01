from django import template

import datetime

register = template.Library()


@register.filter
def is_expired(start_date):
    return datetime.datetime.now().date() >= start_date