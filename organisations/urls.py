from django.urls import path
from . import views

app_name = 'organisations'
urlpatterns = (
    path('view-organisation/', views.create_organisation, name='create_organisation'),
    path('get-gporganisation-data/', views.get_gporganisation_data, name='get_gporganisation_data'),
    path('nhs-autocomplete/', views.get_nhs_autocomplete, name='nhs_autocomplete'),
    path('sign-up-autocomplete/', views.get_sign_up_autocomplete, name='sign_up_autocomplete'),
    path('surgery-management/', views.surgery_management, name='surgery_management'),
    path('get-gp-sign-up-data/', views.get_gp_sign_up_data, name='get_gp_sign_up_data'),
)