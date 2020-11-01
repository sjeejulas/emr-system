from django.urls import path

from . import views

app_name = 'snomedct'
urlpatterns = [
    path('query', views.query_snomed, name='query_snomed'),
    path('readcodes', views.get_readcodes, name='get_readcodes'),
    path('snomed-descendants', views.get_descendants, name='get_descendants'),
    path('descendant-readcodes', views.get_descendant_readcodes, name='get_descendant_readcodes'),
]
