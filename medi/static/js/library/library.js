function clean_modal() {
    $('#errorMessage').empty();
    $('#id_value').removeClass('is-valid is-invalid');
    $('#id_key').removeClass('is-valid is-invalid');
    $('#id_value').val('');
    $('#id_key').val('');
    $('.invalid-feedback').remove();
}

function setup_edit_modal() {
    $('#headerModal').text('Edit word');
    $('#warningHeader').text('Edit word');
    $('#keyLabelInput').text('Word');
    $('#warningMessage').text('Are you sure you wish to edit this Library Entry entry? This will not affect completed' +
        ' reports/records but will affect any \'in progress\' or \'not started\' instructions, unless' +
        ' redactions are already made.');
    $('#continueDeleteButton').attr('href', '#addWordModal');
    $('#continueDeleteButton').attr('data-target', '#addWordModal');
    $('#continueDeleteButton').attr('data-toggle', 'modal');
    $('#continueDeleteButton').attr('data-dismiss', 'modal');
}


function setup_add_modal() {
    $('#keyLabelInput').text('New word');
    $('#headerModal').text('Add new word to the Surgery library');
    $('#addWordForm').attr('action', '');
}