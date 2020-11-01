from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpRequest, HttpResponse, HttpResponseRedirect
from template.forms import TemplateInstructionForm, TemplateQuestionForm,\
        TemplateConditionForm
from template.functions import get_common_with_snomed, create_question,\
        create_condition
from template.models import TemplateInstruction, TemplateAdditionalQuestion,\
        TemplateAdditionalCondition
from template.tables import TemplateTable
from django.forms.models import modelformset_factory
from django_tables2 import RequestConfig
import json
import ast


def create_template(request: HttpRequest) -> JsonResponse:
    if request.method == "POST":
        snomed_concepts = request.POST.getlist('common_condition[]')
        questions = request.POST.getlist('questions[]')
        conditions = request.POST.getlist('addition_condition[]')
        common_ids = []
        if snomed_concepts:
            for snomed in snomed_concepts:
                snomed = ast.literal_eval(snomed)
                common = get_common_with_snomed([snomed])
                if common and common not in common_ids:
                    common_ids.append(common)
        data = {
            'template_title': request.POST.get('template_title'),
            'description': request.POST.get('description'),
            'common_snomed_concepts': common_ids
        }
        template_form = TemplateInstructionForm(data)
        if template_form.is_valid():
            template = template_form.save()
            if questions:
                create_question(template, questions)
            if conditions:
                create_condition(template, conditions)
            if hasattr(request.user, 'userprofilebase') and\
                    hasattr(request.user.userprofilebase, 'clientuser'):
                client_user = request.user.userprofilebase.clientuser
                template.created_by = client_user
                template.organisation = client_user.organisation
                template.save()
            return JsonResponse({
                'error': False,
                'message': 'Template has been created successfully.'
            })
    return JsonResponse({
        'error': True,
        'message': template_form.errors.as_text()
    })


def get_template_data(request: HttpRequest, template_id: str=None) -> JsonResponse:
    if not template_id:
        JsonResponse(status=404)

    data = {'questions': [], 'conditions': [], 'snomed_concepts': []}
    template = get_object_or_404(TemplateInstruction, pk=template_id)

    for addition in template.questions.all():
        data['questions'].append(addition.question)

    for snomed in template.common_snomed_concepts.all():
        data['snomed_concepts'].append(snomed.common_name)

    for condition in template.conditions.all():
        data['conditions'].append({
            'text': condition.snomedct.fsn_description,
            'id': condition.snomedct.external_id
        })

    return JsonResponse(data, status=200)


def view_templates(request: HttpRequest) -> HttpResponse:
    header_title = "Templates"
    try:
        organisation = request.user.userprofilebase.clientuser.organisation
        query = TemplateInstruction.objects.filter(organisation=organisation)
    except:
        query = TemplateInstruction.objects.none()

    table = TemplateTable(query)
    RequestConfig(request, paginate={'per_page': 10}).configure(table)

    return render(request, 'template/view_templates.html', {
        'table': table,
        'header_title': header_title
    })


def remove_template(request: HttpRequest, template_id: str) -> HttpResponseRedirect:
    template = get_object_or_404(TemplateInstruction, pk=template_id)
    template.delete()
    return redirect('template:view_templates')


def edit_template(request: HttpRequest, template_id: str) -> HttpResponse:
    header_title = "Change Template"
    template = get_object_or_404(TemplateInstruction, pk=template_id)
    conditions = template.conditions.all().values_list('snomedct_id', 'snomedct__fsn_description')
    conditions = [cond for cond in conditions]

    if request.method == "POST":
        template_form = TemplateInstructionForm(request.POST, instance=template)
        question_set = modelformset_factory(
            TemplateAdditionalQuestion, TemplateQuestionForm, extra=0
        )
        question_formset = question_set(request.POST, form_kwargs={'empty_permitted': False})
        if template_form.is_valid():
            question_ids = []
            for form in question_formset.forms:
                if form.is_valid():
                    form.save()
                    question_ids.append(form.instance.pk)
                elif not form.instance.pk and form.cleaned_data.get('question'):
                    question = TemplateAdditionalQuestion.objects.create(
                        question=form.cleaned_data.get('question'),
                        template_instruction=template
                    )
                    question_ids.append(question.id)
            TemplateAdditionalQuestion.objects.filter(template_instruction=template).\
                exclude(id__in=question_ids).delete()
            commons = template_form.cleaned_data.get('addition_condition')
            common_ids = []
            for common in commons:
                common_snomed, created = TemplateAdditionalCondition.objects.get_or_create(
                    snomedct_id=int(common),
                    template_instruction=template
                )
                common_ids.append(common_snomed.id)
            TemplateAdditionalCondition.objects.filter(template_instruction=template).\
                exclude(id__in=common_ids).delete()
            template_form.save()
            return redirect('template:view_templates')
    template_form = TemplateInstructionForm(instance=template)
    question_set = modelformset_factory(TemplateAdditionalQuestion, TemplateQuestionForm, extra=1)
    question_formset = question_set(
        queryset=TemplateAdditionalQuestion.objects.filter(template_instruction=template)
    )
    return render(request, 'template/new_template.html', {
        'template_form': template_form,
        'question_formset': question_formset,
        'conditions': json.dumps(conditions),
        'header_title': header_title
    })


def new_template(request:HttpRequest) -> HttpResponse:
    header_title = "New Template"
    template_form = TemplateInstructionForm()
    question_set = modelformset_factory(TemplateAdditionalQuestion, TemplateQuestionForm, extra=1)
    question_formset = question_set(queryset=TemplateAdditionalQuestion.objects.none())

    if request.method == "POST":
        template_form = TemplateInstructionForm(request.POST)
        question_set = modelformset_factory(
                TemplateAdditionalQuestion, TemplateQuestionForm, extra=0
        )
        question_formset = question_set(request.POST, form_kwargs={'empty_permitted': False})
        if template_form.is_valid():
            template = template_form.save()
            if hasattr(request.user, 'userprofilebase') and\
                    hasattr(request.user.userprofilebase, 'clientuser'):
                client_user = request.user.userprofilebase.clientuser
                template.organisation = client_user.organisation
                template.created_by = client_user
                template.save()
            for form in question_formset.forms:
                form.is_valid()
                if form.cleaned_data.get('question'):
                    TemplateAdditionalQuestion.objects.create(
                        question=form.cleaned_data.get('question'),
                        template_instruction=template
                    )
            if template_form.cleaned_data.get('addition_condition'):
                commons = template_form.cleaned_data.get('addition_condition')
                for common in commons:
                    common_snomed, created = TemplateAdditionalCondition.objects.get_or_create(
                        snomedct_id=int(common),
                        template_instruction=template
                    )
            return redirect('template:view_templates')
    return render(request, 'template/new_template.html', {
        'template_form': template_form,
        'question_formset': question_formset,
        'conditions': [],
        'header_title': header_title
    })
