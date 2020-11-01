from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django_tables2 import RequestConfig
from django.db.models import Q
from django.db import IntegrityError
from django.http import JsonResponse

from instructions.models import Instruction
from instructions.views import calculate_next_prev
from medicalreport.models import AmendmentsForRecord

from .models import Library, LibraryHistory
from .tables import LibraryTable
from .forms import LibraryForm


@login_required(login_url='/accounts/login')
def edit_library(request, event):
    header_title = "Surgery Library"
    page_length = 10
    search_input = ''
    gp_practice = request.user.userprofilebase.generalpracticeuser.organisation
    library = Library.objects.filter(gp_practice=gp_practice)
    library_form = LibraryForm(gp_org_id=gp_practice.pk)
    add_word_error_message = ''
    edit_word_error_message = ''
    error_edit_link = ''
    if request.method == 'POST':
        library_form = LibraryForm(request.POST, gp_org_id=gp_practice.pk)
        if library_form.is_valid():
            library_obj = library_form.save(commit=False)
            library_obj.gp_practice = gp_practice
            library_obj.save()
            library_form = LibraryForm(gp_org_id=gp_practice.pk)
            if event == 'add' and request.is_ajax():
                return JsonResponse({'message': 'A word has been created.'})
            messages.success(request, 'Add word successfully')
        else:
            add_word_error_message = 'This word already exist in your library. If you wish to edit it, please go back ' \
                                      'to the library and edit from there'
            if event == 'add' and request.is_ajax():
                return JsonResponse({'message': 'Error', 'add_word_error_message': add_word_error_message})

    if 'page_length' in request.GET:
        page_length = int(request.GET.get('page_length'))

    if 'search' in request.GET:
        search_input = request.GET.get('search')
        library = library.filter(Q(key__icontains=search_input) | Q(value__icontains=search_input))
        event = 'index'

    if event.split(':')[0] == 'edit_error':
        error_edit_id = event.split(':')[1]
        error_libray = Library.objects.get(id=error_edit_id)
        library_form = LibraryForm(instance=error_libray)
        error_edit_link = reverse('library:edit_word_library', kwargs={'library_id': error_edit_id})
        edit_word_error_message = 'This word already exist in your library. If you wish to edit it, please go back ' \
                                  'to the library and edit from there'

    table = LibraryTable(library)
    RequestConfig(request, paginate={'per_page': page_length}).configure(table)
    next_prev_data = calculate_next_prev(table.page,  page_length=page_length)

    return render(request, 'library/edit_library.html', {
        'header_title': header_title,
        'table': table,
        'next_prev_data': next_prev_data,
        'page_length': page_length,
        'search_input': search_input,
        'library_form': library_form,
        'event': event,
        'add_word_error_message': add_word_error_message,
        'edit_word_error_message': edit_word_error_message,
        'error_edit_link': error_edit_link
    })


@login_required(login_url='/accounts/login')
def delete_library(request, library_id):
    library = get_object_or_404(Library, pk=library_id)
    library.hard_delete()

    return redirect('library:edit_library', event='delete')


@login_required(login_url='/accounts/login')
def edit_word_library(request, library_id):
    library = get_object_or_404(Library, pk=library_id)
    library.key = request.POST.get('key')
    library.value = request.POST.get('value')
    event = 'edit'
    try:
        library.save()
        messages.success(request, 'Update word successfully')
    except IntegrityError as e:
        event = 'edit_error:{id}'.format(id=library.id)

    return redirect('library:edit_library', event=event)


@login_required(login_url='/accounts/login')
def redact_word(request):
    if request.is_ajax():
        try:
            word = request.GET.get('word').strip()
            instruction_id = request.GET.get('instruction_id')
            idx = request.GET.get('idx')
            guid = request.GET.get('guid')
            section = request.GET.get('section')
            xpath = request.GET.get('xpath')

            instruction = Instruction.objects.get(pk=instruction_id)
            LibraryHistory.objects.create(
                instruction=instruction,
                action=LibraryHistory.ACTION_HIGHLIGHT_REDACT,
                old=word,
                new='',
                guid=guid,
                index=idx,
                section=section,
                xpath=xpath
            )
            return JsonResponse({'message': 'Redact completed.'})
        except Exception as e:
            return JsonResponse({'message': 'Error: {e}'.format(e=e)}, status=500)


@login_required(login_url='/accounts/login')
def replace_word(request):
    if request.is_ajax():
        try:
            word = request.GET.get('word').strip()
            instruction_id = request.GET.get('instruction_id')
            idx = request.GET.get('idx')
            guid = request.GET.get('guid')
            section = request.GET.get('section')
            xpath = request.GET.get('xpath')

            instruction = Instruction.objects.get(pk=instruction_id)
            library = Library.objects.filter(key__iexact=word).first()
            LibraryHistory.objects.create(
                instruction=instruction,
                action=LibraryHistory.ACTION_REPLACE,
                old=word,
                new=library.value,
                guid=guid,
                index=idx,
                section=section,
                xpath=xpath
            )
            return JsonResponse({'message': 'Replace completed.', 'replace_word': library.value})
        except Exception as e:
            return JsonResponse({'message': 'Error: {e}'.format(e=e)}, status=500)


@login_required(login_url='/accounts/login')
def replace_allword(request):
    if request.is_ajax():
        try:
            word = request.GET.get('word').strip()
            instruction_id = request.GET.get('instruction_id')
            gp_practice = request.user.userprofilebase.generalpracticeuser.organisation
            library = Library.objects.filter(gp_practice=gp_practice, key__iexact=word).first()

            instruction = Instruction.objects.get(pk=instruction_id)
            LibraryHistory.objects.create(
                instruction=instruction,
                action=LibraryHistory.ACTION_REPLACE_ALL,
                old=word,
                new=library.value,
            )
            return JsonResponse({'message': 'Replace all completed.', 'replace_word': library.value})
        except Exception as e:
            return JsonResponse({'message': 'Error: {e}'.format(e=e)}, status=500)


@login_required(login_url='/accounts/login')
def undo_last(request):
    if request.is_ajax():
        try:
            instruction_id = request.GET.get('instruction_id')
            instruction = Instruction.objects.get(pk=instruction_id)
            recent_history = LibraryHistory.objects.filter(instruction=instruction).last()
            if recent_history:
                if recent_history.old and not Library.objects.get(key__iexact=recent_history.old).value:
                    highlight_html = '''
                        <span class="bg-warning">{}</span>
                        <span class="dropdown-options" dummy-guid dummy-word_idx dummy-section>
                            <a href="#/" class="highlight-redact">Redact</a>
                    '''.format(recent_history.old)
                else:
                    highlight_html = '''
                        <span class="bg-warning">{}</span>
                        <span class="dropdown-options" dummy-guid dummy-word_idx dummy-section>
                            <a href="#/" class="highlight-redact">Redact</a>
                            <a href="#/" class="highlight-replace">Replace</a>
                            <a href="#/" class="highlight-replaceall">Replace all</a>
                        </span>
                    '''.format(recent_history.old)
                data = {
                    'action': recent_history.action,
                    'old': recent_history.old,
                    'new': recent_history.new,
                    'text': highlight_html,
                    'guid': recent_history.guid,
                    'word_idx': recent_history.index,
                    'section': recent_history.section,
                }
                recent_history.hard_delete()
                return JsonResponse(data)
            return JsonResponse({'message': 'No redaction history left for this instruction'}, status=500)
        except Exception as e:
            return JsonResponse({'message': 'Error: {e}'.format(e=e)}, status=500)


@login_required(login_url='/accounts/login')
def undo_all(request):
    if request.is_ajax():
        try:
            instruction_id = request.GET.get('instruction_id')
            instruction = Instruction.objects.get(pk=instruction_id)

            new_replace_words = list(LibraryHistory.objects.filter(
                Q(action=LibraryHistory.ACTION_REPLACE) | Q(action=LibraryHistory.ACTION_REPLACE_ALL)
            ).values_list('new', flat=True))

            old_replace_words = list(LibraryHistory.objects.filter(
                Q(action=LibraryHistory.ACTION_REPLACE) | Q(action=LibraryHistory.ACTION_REPLACE_ALL)
            ).values_list('old', flat=True))

            upper_new_replace_words = list(map(lambda x: x.upper(), new_replace_words))

            # clear all Library history
            LibraryHistory.objects.filter(instruction=instruction).hard_delete()

            # clear all redacted xpaths
            AmendmentsForRecord.objects.filter(instruction=instruction).update(redacted_xpaths=[])
            return JsonResponse({
                'message': 'Undo all completed.',
                'new_replace_words': upper_new_replace_words,
                'old_replace_words': old_replace_words,
            })
        except Exception as e:
            return JsonResponse({'message': 'Error: {e}'.format(e=e)}, status=500)


@login_required(login_url='/accounts/login')
def manual_redact(request):
    if request.is_ajax():
        try:
            instruction_id = request.GET.get('instruction_id')
            guid = request.GET.get('guid')
            section = request.GET.get('section')
            action = request.GET.get('action')

            instruction = Instruction.objects.get(pk=instruction_id)
            library_history = LibraryHistory(
                instruction=instruction,
                action=action,
                guid=guid,
                section=section
            )
            library_history.save()
            return JsonResponse({'message': 'Complete'})
        except Exception as e:
            return JsonResponse({'message': 'Error: {e}'.format(e=e)}, status=500)
