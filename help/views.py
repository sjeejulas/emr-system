from django.http import HttpResponse
from django.shortcuts import render


def resource_centre(request):
    title = 'Resource Centre'
    return render(request, 'help/menu.html', {
        'header_title': title,
    })