from django.utils.html import format_html
from django.shortcuts import reverse

from .models import Library

import django_tables2 as tables


class LibraryTable(tables.Table):
    edit_button = tables.Column(empty_values=(), verbose_name='', attrs={'td': {'style': 'width:95px;text-align: center;'}})
    delete_button = tables.Column(empty_values=(), verbose_name='', attrs={'td': {'style': 'width:95px;text-align: center;'}})

    class Meta:
        attrs = {
            'class': 'table table-bordered table-hover',
            'id': 'libraryTable'
        }
        model = Library
        fields = (
            'key', 'value'
        )

    def render_edit_button(self, record):
        return format_html(
            '<button data-editLink="{edit_library_url}" class="btn btn-fee text-light btn-sm editButton" style="width:80px;">EDIT</button>'.format(
                edit_library_url=reverse('library:edit_word_library', kwargs={'library_id': record.id})
            )
        )

    def render_delete_button(self, record):
        return format_html(
            '<button data-deleteLink="{delete_library_url}" class="btn btn-danger btn-sm deleteButton" data-toggle="modal" '
            'data-target="#warningModal" style="width:90px;"><i class="fas fa-times"></i>&nbsp;REMOVE</button>'.format(
                delete_library_url=reverse('library:delete_library', kwargs={'library_id': record.id})
            )
        )


