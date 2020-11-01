from django import template


register = template.Library()


def sensor_phone(phone):
    if phone:
        number = ["*"] * (len(phone) - 2)
        number.append(phone[-2:])
        number = " ".join(map(str, number))
        return number
    return ""


register.filter('sensor_phone', sensor_phone)
