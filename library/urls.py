from django.urls import path
from . import views

app_name = 'library'
urlpatterns = (
    path('mredact/', views.manual_redact, name='manual_radact'),
    path('redact/', views.redact_word, name='redact_word'),
    path('replace/', views.replace_word, name='replace_word'),
    path('replaceall/', views.replace_allword, name='replace_allword'),
    path('undolast/', views.undo_last, name='undo_last'),
    path('undoall/', views.undo_all, name='undo_all'),
    path('<str:event>/', views.edit_library, name='edit_library'),
    path('delete/<int:library_id>/', views.delete_library, name='delete_library'),
    path('edit/<int:library_id>/', views.edit_word_library, name='edit_word_library'),
)