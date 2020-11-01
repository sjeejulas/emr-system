import django_filters as filters
from .models import Instruction


class InstructionFilter(filters.FilterSet):

    class Meta:
        model = Instruction
        fields = ('id', 'type')
