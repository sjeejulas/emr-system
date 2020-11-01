from django.contrib import admin
from template.models import TemplateInstruction, TemplateAdditionalQuestion, TemplateAdditionalCondition


class AdditionQuestionInline(admin.StackedInline):
    model = TemplateAdditionalQuestion
    verbose_name = "Additional Question"
    extra = 1


class AdditionConditionInline(admin.StackedInline):
    model = TemplateAdditionalCondition
    raw_id_fields = ('snomedct',)
    verbose_name = "Additional Condition"
    extra = 1


class TemplateInstructionAdmin(admin.ModelAdmin):
    inlines = [AdditionQuestionInline, AdditionConditionInline]
    filter_horizontal = ('common_snomed_concepts',)


admin.site.register(TemplateInstruction, TemplateInstructionAdmin)
