from django.contrib import admin
from .models import CommonSnomedConcepts, SnomedConcept, SnomedDescendant, ReadCode


# Register your models here.
class SnomedConceptsAdmin(admin.ModelAdmin):
    ordering = ['external_id']
    search_fields = ['external_id' ,'fsn_description']


class SnomedDescendantsAdmin(admin.ModelAdmin):
    ordering = ['id']
    search_fields = ['external_id']
    raw_id_fields = ("descendant_external_id",)


class ReadCodeAdmin(admin.ModelAdmin):
    ordering = ['id']
    search_fields = ['ext_read_code']
    raw_id_fields = ("concept_id",)


class CommonSnomedConceptsAdmin(admin.ModelAdmin):
    raw_id_fields = ('snomed_concept_code', )
    fields = ('common_name', 'snomed_concept_code')


admin.site.register(SnomedConcept, SnomedConceptsAdmin)
# admin.site.register(SnomedDescendant, SnomedDescendantsAdmin)
# admin.site.register(ReadCode, ReadCodeAdmin)
admin.site.register(CommonSnomedConcepts, CommonSnomedConceptsAdmin)
