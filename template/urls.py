from django.urls import path
from . import views

app_name = 'template'
urlpatterns = (
    path('create-template/', views.create_template, name='create_template'),
    path('get-template-data/<int:template_id>', views.get_template_data, name='get_template_data'),
    path('remove-template/<int:template_id>', views.remove_template, name='remove_template'),
    path('edit-template/<int:template_id>', views.edit_template, name='edit_template'),
    path('new-template/', views.new_template, name='new_template'),
    path('view-templates/', views.view_templates, name='view_templates')
)
