from django.urls import path

from . import views

app_name = 'services'
urlpatterns = [
    path('getpatientlist', views.get_patient_list, name='getpatientlist'),
    path('getpatientrecord', views.get_patient_record, name='getpatientrecord'),
    path('getpatientattachment', views.get_patient_attachment, name='getpatientattachment'),
    path('errors/<int:code>/', views.handle_error, name='handle_error')
]
