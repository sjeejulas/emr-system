function isValid(){
  var is_allow = true;
  $('.input-invalid').removeClass('input-invalid');
  if ($('#ch-confirmed-agreement').is(':checked')) {
      if ($('#id_patient_email').val() == '') {
        $('#id_patient_email').addClass('input-invalid');
        is_allow = false;
      }   
      if ($('#confirm_email').val() == '') {
        $('#confirm_email').addClass('input-invalid');
        is_allow = false;
      }   
      if ($('#id_patient_telephone_mobile').val() == '') {
        $('#id_patient_telephone_mobile').addClass('input-invalid');
        is_allow = false;
      }   
  }   
  if ($('#ch-report-third-party').is(':checked')) {
      if ($('#id_email_1').val() == '') {
        $('#id_email_1').addClass('input-invalid');
        is_allow = false;
      }   
      if ($('#id_email_2').val() == '') {
        $('#id_email_2').addClass('input-invalid');
        is_allow = false;
      }   
      if ($('#id_office_phone_number').val() == '') {
        $('#id_office_phone_number').addClass('input-invalid');
        is_allow = false;
      }   
      if ($('#id_contact_name').val() == '') {
        $('#id_contact_name').addClass('input-invalid');
        is_allow = false;
      }   
  }
  return is_allow;
}

function initialData(patientNotification, thirdPartyNotification){
  $('#ch-confirmed-agreement').bind('click dblclick', function(evt) {
      if ($(this).is(':checked')) {
          $('#collapse-to-patient').slideDown('slow');
      } else {
          $('#collapse-to-patient').slideUp('slow');
      }
  });

  $('#ch-report-third-party').bind('click dblclick', function(evt) {
      if ($(this).is(':checked')) {
          $('#third-party-section').slideDown('slow');
      } else {
          $('#third-party-section').slideUp('slow');
      }
  });

  if(patientNotification == 'True') {
    $('#ch-confirmed-agreement').click();
  }

  if(thirdPartyNotification == 'True') {
    $('#ch-report-third-party').click();
  }
}

function hidenReport(){
  var element = $('.reports.active');
  var reportID = $(element).attr('id').replace('report-', '');
  $('.attachments').hide();
  $('#attachment-' + reportID).hide();
}

function showHidenReport(){
  var element = $('.reports.active');
  var reportID = $(element).attr('id').replace('report-', '');
  $('.reports').removeClass('active');
  $('#report-' + reportID).addClass('active');
  $('.attachments').hide();
  $('#attachment-' + reportID).show();
}
