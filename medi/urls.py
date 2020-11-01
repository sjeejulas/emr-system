"""medi URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls import handler404, handler500

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from instructions.views import instruction_pipeline_view
from accounts.functions import notify_password_changed
from django.contrib.auth import views as auth_views
from accounts import views as account_views
from common import health


admin.site.site_header = 'MediData administration'
admin.site.site_title = 'MediData administration'


urlpatterns = [
    path('', instruction_pipeline_view, name='view_pipeline'),
    path('testservices/', include('services.urls')),
    path('medicalreport/', include('medicalreport.urls')),
    path('snomedct/', include('snomedct.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('instruction/', include('instructions.urls', namespace='instructions')),
    path('onboarding/', include('onboarding.urls', namespace='onboarding')),
    path('organisation/', include('organisations.urls', namespace='organisations')),
    path('template/', include('template.urls', namespace='template')),
    path('report/', include('report.urls', namespace='report')),
    path('select2/', include('django_select2.urls')),
    path('login/', account_views.login, name='login'),
    path('password_change/done/', notify_password_changed(auth_views.PasswordChangeDoneView.as_view()), name='password_change_done'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('resource_centre/', include('help.urls', namespace='help')),
    path('library/', include('library.urls', namespace='library')),
    path('health-check/', health.health_check, name='health_check')
]
#urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += staticfiles_urlpatterns()

handler404 = 'services.views.handler_404'
handler500 = 'services.views.handler_500'
