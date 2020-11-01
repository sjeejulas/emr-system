from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def keyvalue(dict, key):
    if key in dict:
        return dict[key]


def format_date(date):
    if date is None:
        return ''
    return date.strftime("%H:%M %d %b %Y")


register.filter('format_date', format_date)


@register.filter
def patient_full_name(user):
    full_name = [user.patient_title, user.patient_first_name, user.patient_last_name]
    full_name = list(filter(None, full_name))
    return " ".join(full_name)


@register.filter
def gp_surgery_full_name(surgery):
    address_lines = [surgery.billing_address_street, surgery.billing_address_city,
                     surgery.billing_address_state, surgery.billing_address_postalcode]
    address_lines = list(filter(None, address_lines))
    return format_html('{}<br>{}', surgery.name, " ".join(address_lines))
