from django.urls import path

from . import views

app_name = 'report'
urlpatterns = [
    path('select-report/<str:access_type>', views.get_report, name='select-report'),
    path('<int:report_auth_id>/third-party-authorisation', views.add_third_party_authorisation, name='add-third-party'),
    path('<int:instruction_id>/<str:access_type>/<str:url>', views.sar_request_code, name='request-code'),
    path('access-code/<str:access_type>/<str:url>', views.sar_access_code, name='access-code'),
    path('access-failed', views.sar_access_failed, name='access-failed'),
    path('session-expired', views.session_expired, name='session-expired'),
    path('summary-report', views.summry_report, name='summary-report'),
    path('cancel-authorisation/<int:third_party_authorisation_id>', views.cancel_authorisation, name='cancel-authorisation'),
    path('extend-authorisation/<int:third_party_authorisation_id>', views.extend_authorisation, name='extend-authorisation'),
    path('renew-authorisation/<int:third_party_authorisation_id>', views.renew_authorisation, name='renew-authorisation')
]
