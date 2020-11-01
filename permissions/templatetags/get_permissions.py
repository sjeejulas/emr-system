from django import template
from accounts.models import GENERAL_PRACTICE_USER, User
from instructions.models import Instruction
from instructions.model_choices import AMRA_TYPE, SARS_TYPE
register = template.Library()


def reject_instruction(user_id, instruction_id):
    permission = False
    user = User.objects.get(pk=user_id)
    instruction = Instruction.objects.get(pk=instruction_id)
    if user.type != GENERAL_PRACTICE_USER:
        return permission
    if instruction.type == AMRA_TYPE and user.has_perm('instructions.reject_amra'):
        permission = True
    elif instruction.type == SARS_TYPE and user.has_perm('instructions.reject_sars'):
        permission = True
    return permission


def process_instruction(user_id, instruction_id):
    permission = False
    user = User.objects.get(pk=user_id)
    instruction = Instruction.objects.get(pk=instruction_id)
    if user.type != GENERAL_PRACTICE_USER:
        return permission
    if instruction.type == AMRA_TYPE and user.has_perm('instructions.process_amra'):
        permission = True
    elif instruction.type == SARS_TYPE and user.has_perm('instructions.process_sars'):
        permission = True
    return permission


def sign_off_report(user_id, instruction_id):
    permission = False
    user = User.objects.get(pk=user_id)
    instruction = Instruction.objects.get(pk=instruction_id)
    if user.type != GENERAL_PRACTICE_USER:
        return permission
    if instruction.type == AMRA_TYPE and user.has_perm('instructions.sign_off_amra'):
        permission = True
    elif instruction.type == SARS_TYPE and user.has_perm('instructions.sign_off_sars'):
        permission = True
    return permission


def view_complete_report(user_id, instruction_id):
    permission = False
    user = User.objects.get(pk=user_id)
    instruction = Instruction.objects.get(pk=instruction_id)
    if user.type != GENERAL_PRACTICE_USER:
        return permission
    if instruction.type == AMRA_TYPE and user.has_perm('instructions.view_completed_amra'):
        permission = True
    elif instruction.type == SARS_TYPE and user.has_perm('instructions.view_completed_sars'):
        permission = True
    return permission


register.filter('reject_instruction', reject_instruction)
register.filter('process_instruction', process_instruction)
register.filter('sign_off_report', sign_off_report)
