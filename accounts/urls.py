from django.urls import path
from . import views
from accounts.functions import notify_password_reset
from django.contrib.auth import views as auth_views

app_name = 'accounts'
urlpatterns = (
    path('locked/', views.locked_out, name='locked_out'),
    path('view-account/', views.account_view, name='view_account'),
    path('view-fee/', views.account_view, name='view_fee'),
    path('view-users/', views.view_users, name='view_users'),
    path('view-profile/', views.view_profile, name='view_profile'),
    path('create-user/', views.create_user, name='create_user'),
    path('medi-create-user/', views.medi_create_user, name='medi_create_user'),
    path('medi-change-user/<str:email>', views.medi_change_user, name='medi_change_user'),
    path('manage-user/', views.manage_user, name='manage_user'),
    path('verify-password/', views.verify_password, name='verify_password'),
    path('update-permission/', views.update_permission, name='update_permission'),
    path('update-notification/', views.update_notification, name='update_notification'),
    path('check-email/', views.check_email, name='check_email'),
    path('login/', views.login, name='login'),
    path('two-factor/', views.two_factor, name='two_factor'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password-reset/', notify_password_reset(auth_views.PasswordResetView.as_view()), name='password_reset'),
    path('password-change/', auth_views.PasswordChangeView.as_view(), name='password_change')
)
