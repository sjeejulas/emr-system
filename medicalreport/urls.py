from django.urls import path

from . import views

app_name = 'medicalreport'
urlpatterns = [
    path('<int:instruction_id>/patient-emis-number/', views.set_patient_emis_number, name='set_patient_emis_number'),
    path('<int:instruction_id>/select-patient/<int:patient_emis_number>/', views.select_patient, name='select_patient'),
    path('<int:instruction_id>/reject-request/', views.reject_request, name='reject_request'),
    path('<int:instruction_id>/edit/', views.edit_report, name='edit_report'),
    path('<int:instruction_id>/submit-report/', views.submit_report, name='submit_report'),
    path('<int:instruction_id>/final-report/', views.final_report, name='final_report'),
    path('<int:instruction_id>/view-report/', views.view_report, name='view_report'),
    path('<int:instruction_id>/view-consent-pdf/', views.view_consent_pdf, name='view_consent_pdf'),
    path('<int:instruction_id>/view-total-report/', views.view_total_report, name='view_total_report'),
    path('<int:instruction_id>/update/', views.update_report, name='update_report'),
    path('<int:instruction_id>/attachment/<str:path_file>', views.view_attachment, name='view_attachment'),
    path('<int:instruction_id>/download-attachment/<str:path_file>', views.download_attachment, name='download_attachment'),
    path('<int:instruction_id>/download-medicalreport/', views.download_medicalreport, name='download_medicalreport'),
    path('trud-ivf', views.trud_ivf, name="trud_ivf"),
    path('trud-std', views.trud_std, name="trud_std"),
    path('trud-other', views.trud_other, name="trud_other"),
]
