from django import forms
from django.contrib import admin
from django.contrib.messages import get_messages
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect
from django.urls import path
from axes.models import AccessAttempt

from permissions.models import InstructionPermission
from .models import *


class ClientProfileInline(admin.StackedInline):
    model = ClientUser
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class GeneralPracticeProfileInline(admin.StackedInline):
    model = GeneralPracticeUser
    raw_id_fields = ('organisation',)
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class MedidataProfileInline(admin.StackedInline):
    model = MedidataUser
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'type')
        field_classes = {''}


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'password', 'groups', 'is_active',)


class WhitelistAdmin(admin.ModelAdmin):
    list_display = ('from_ip', 'to_ip',)
    list_filter = ('from_ip', )
    change_list_template = "admin/change_list.html"


class UserAdmin(BaseUserAdmin):
    inlines = []
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = ('email', 'first_name', 'last_name', 'type', 'is_active')
    list_filter = ('type',)
    change_list_template = "admin/accounts/change_list.html"

    class Media():
        js = ('js/custom_admin/add_user.js', )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('update-permissions/', self.update_permissions)
        ]
        return my_urls + urls

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return self.readonly_fields + ('groups', 'user_permissions')
        return self.readonly_fields

    def get_queryset(self, request):
        if hasattr(request.user, 'userprofilebase'):
            queryset = request.user.get_query_set_within_organisation()
            return queryset
        return super().get_queryset(request)

    def get_inline_instances(self, request, obj=None):
        self.inlines = []
        GeneralPracticeProfileInline.readonly_fields = []
        ClientProfileInline.readonly_fields = []
        if not obj:
            self.inlines.append(ClientProfileInline)
            self.inlines.append(GeneralPracticeProfileInline)
            self.inlines.append(MedidataProfileInline)
        else:
            if request.user.type != MEDIDATA_USER and not request.user.is_superuser:
                GeneralPracticeProfileInline.readonly_fields = ['organisation']
                ClientProfileInline.readonly_fields = ['organisation']
            # dynamic user profile form by User type
            if obj.type == CLIENT_USER:
                self.inlines.append(ClientProfileInline)
            elif obj.type == GENERAL_PRACTICE_USER:
                self.inlines.append(GeneralPracticeProfileInline)
            else:
                self.inlines.append(MedidataProfileInline)
        return super(UserAdmin, self).get_inline_instances(request, obj)

    def get_fieldsets(self, request, obj=None):
        self.add_fieldsets = (
            (None, {
                'classes': ('wide',),
                'fields': ('email', 'username', 'password1', 'password2', 'first_name', 'last_name'),
            }),
        )
        self.fieldsets = (
            (None, {'fields': ('email', 'password')}),
            ('Personal info', {'fields': ('first_name', 'last_name')}),
        )

        if request.user.type == MEDIDATA_USER or request.user.is_superuser:
            # add permission form
            self.fieldsets = (
                (None, {'fields': ('email', 'password')}),
                ('Personal info', {'fields': ('first_name', 'last_name')}),
                ('Permissions', {'fields': ('is_active', 'groups', 'user_permissions')}),
            )
            # add type field form
            self.add_fieldsets = (
                (None, {
                    'classes': ('wide',),
                    'fields': ('email', 'username', 'password1', 'password2', 'first_name', 'last_name', 'type')}),
            )

        if not obj:
            return self.add_fieldsets

        return super().get_fieldsets(request, obj)

    def save_model(self, request, obj, form, change):
        if request.user.type == CLIENT_USER:
            obj.type = CLIENT_USER
            super(UserAdmin, self).save_model(request, obj, form, change)
            if hasattr(request.user, 'userprofilebase'):
                if not ClientUser.objects.filter(user=obj).exists():
                    organisation = request.user.userprofilebase.clientuser.organisation
                    ClientUser.objects.create(user=obj, organisation=organisation)
        elif request.user.type == GENERAL_PRACTICE_USER:
            obj.type = GENERAL_PRACTICE_USER
            super(UserAdmin, self).save_model(request, obj, form, change)
            if hasattr(request.user, 'userprofilebase'):
                if not GeneralPracticeUser.objects.filter(user=obj).exists():
                    organisation = request.user.userprofilebase.generalpracticeuser.organisation
                    GeneralPracticeUser.objects.create(user=obj, organisation=organisation)
        else:
            super(UserAdmin, self).save_model(request, obj, form, change)

    def update_permissions(self, request):
        for client in ClientUser.objects.all():
            client.update_permission()
        for gp in GeneralPracticeUser.objects.all():
            gp.update_permission()
        for medi in MedidataUser.objects.all():
            medi.update_permission()
        self.message_user(request, "Update permissions successfully.")
        return redirect('/admin/accounts/user/')


class PatientAdmin(admin.ModelAdmin):
    raw_id_fields = ('organisation_gp',)


class AccessAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'attempt_time',
        'ip_address',
        'user_agent',
        'username',
        'path_info',
        'failures_since_start',
    )

    list_filter = [
        'attempt_time',
        'path_info',
    ]

    search_fields = [
        'ip_address',
        'username',
        'user_agent',
        'path_info',
    ]

    date_hierarchy = 'attempt_time'

    fieldsets = (
        (None, {
            'fields': ('path_info', 'failures_since_start')
        }),
        (_('Form Data'), {
            'fields': ('get_data', 'post_data')
        }),
        (_('Meta Data'), {
            'fields': ('user_agent', 'ip_address', 'http_accept')
        })
    )

    readonly_fields = [
        'user_agent',
        'ip_address',
        'username',
        'http_accept',
        'path_info',
        'attempt_time',
        'get_data',
        'post_data',
    ]

    def has_add_permission(self, request):
        return False


admin.site.unregister(AccessAttempt)
admin.site.register(AccessAttempt, AccessAttemptAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Patient, PatientAdmin)
admin.site.register(Whitelist, WhitelistAdmin)
