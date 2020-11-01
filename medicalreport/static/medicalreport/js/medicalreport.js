function updateRejectType(element) {
    var rejectID = $(element).attr('id').replace('rejected_reason-', '');
    $('#rejected_reason').val(rejectID);
}

function renderReport(element) {
    var reportID = $(element).attr('id').replace('report-', '');
    $('.reports').removeClass('active');
    $('#report-' + reportID).addClass('active');
    $('.attachments').hide();
    $('#attachment-' + reportID).show();
}

function subMitMedicalReport(event) {
    if (event == "draft") {
        $('#event_flag').val('draft');
        $('#medicalReportForm').submit();
    } else if (event == "preview") {
        $('#event_flag').val('preview');
        $('#medicalReportForm').submit();
    } else if (event == "add-medication") {
        $('#id_prepared_by').removeAttr("required");
        $('#addMedicationButton').prop("disabled", true);
        $('#event_flag').val("add-medication");
        $('#medicalReportForm').submit();
    } else if (event == "add-allergies") {
        $('#id_prepared_by').removeAttr("required");
        $('#addAllergiesButton').prop("disabled", true);
        $('#event_flag').val("add-allergies");
        $('#medicalReportForm').submit();
    } else {
        $('.attachments').hide();
        $('#confirmSubmitModal').modal("show");
    }
}

function submitConfirmReport(event) {
    if (event == "confirm") {
        if (!$('#accept_disclaimer').is(':checked')) {
            $('#confirmSubmitModal').modal('hide');
            create_alert('Please accept the Medidata Exchange Ltd disclaimer.', 'error');
            return false;
        }
        $('#event_flag').val('submit');
        $('#overlay').show();
        $('#medicalReportForm').submit();
        $('#confirmSubmitModal').modal('hide');
    } else {
        $('#confirmSubmitModal').modal('hide');
        create_alert('Invalid action. Please contact admin.', 'error');
        return false;
    }
}

function showHiddenReport() {
    var el = $('.reports.active');
    renderReport(el);
}

function saveReport() {
    var inst = arguments.length > 1 && arguments[0] !== undefined ? arguments[0] : false;
    var post_url = $('#medicalReportForm').attr("action"); //get form action url
    var request_method = $('#medicalReportForm').attr("method"); //get form GET/POST method
    var form_data = $('#medicalReportForm').serialize(); //Encode form elements for submission
    $.ajax({
        url: post_url,
        type: request_method,
        data: form_data
    }).done(function() {
        if (!inst) {
            create_alert('Report has been saved.', 'success');
        }
    }).fail(function() {
        create_alert('Something went wrong, please try again.', 'error');
    });
}

function addWordLibrary() {
    var post_url = $('#addWordForm').attr("action"); //get form action url
    var request_method = $('#addWordForm').attr("method"); //get form GET/POST method
    var form_data = $('#addWordForm').serialize(); //Encode form elements for submission
    $.ajax({
        url: post_url,
        type: request_method,
        data: form_data
    }).done(function(response) {
        if (typeof response['add_word_error_message'] != 'undefined') {
            $('#errorMessage').text(response['add_word_error_message']);
        } else {
            $('#errorMessage').text('');
            create_alert(response['message'], 'success');
            $("#addWordModal").modal('hide');
        }
    }).fail(function() {
        create_alert('Something went wrong, please try again.', 'error');
    });
}

function fetchAttachments(url) {
  var attachments = $('.attachment-not-active');
  attachments.each(function(index, attachment) {
    var ajax_url = url;
    var instructionID = attachment.getAttribute('instruction');
    var attachmentID = attachment.getAttribute('attachment');
    ajax_url = ajax_url.replace(1, instructionID);
    ajax_url = ajax_url.replace('path', attachmentID);
    $.ajax({
      url: ajax_url
    }).done(function(response) {
      if (response['have_report']) {
        $('a[attachment="'+attachmentID+'"]').removeClass('attachment-not-active');
        $('a[attachment="'+attachmentID+'"]').removeAttr('onclick');
        $('a[attachment="'+attachmentID+'"]').attr('title', 'Preview');
        var title_el = $('a[attachment="'+attachmentID+'"]').next().find('span.redaction-checkbox__header')[0];
        var title_text = title_el.title;
        if (response['redacted_count'] > 0) {
          $('span[title="' + title_text + '"]').append('<div class="numberCircle">' + response['redacted_count'] + '</div>');
        }
        create_alert('Attachment ' + title_text + ' redacted', 'success');
      }
    });
  });
}
