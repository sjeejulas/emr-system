from django.contrib import admin
from django import forms
from .models import SiteAccessControl


class SiteControlAccessForm(forms.ModelForm):
    class Meta:
        model = SiteAccessControl
        fields = '__all__'


class SiteControlAccessAdmin(admin.ModelAdmin):
    form = SiteControlAccessForm
    fieldsets = (
        ('Site Information', {'fields': ('site_host', 'gp_access', 'client_access', 'patient_access',
        'medi_access', 'active_host')}),
    )

admin.site.register(SiteAccessControl, SiteControlAccessAdmin)
