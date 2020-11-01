function render_common_conditions(){
  $('#id_common_snomed_concepts').addClass('row');
  $('#id_common_snomed_concepts .checkbox').addClass('form-control-sm d-inline col-md-3');
}

function render_addition_conditions(conditions){
  if(conditions !== undefined){
      conditions.forEach(function(condition, index) {
          $('#id_addition_condition').append(new Option(condition[1], condition[0], true, true)).trigger('change');
      });
  };
}
