
function init_select2_postcode(init_data) {
    $('#id_postcode').select2({
        data: init_data,
        ajax: {
            url: function (params) {
                return "https://api.postcodes.io/postcodes/"+ params.term +"/autocomplete"
            },
            processResults: function (data) {
                let formed_data = [];
                for(let i=0; i < data['result'].length; i++){
                    formed_data.push({'id': data['result'][i], 'text': data['result'][i]});
                }
                return {
                    results: formed_data
                }
            }
        }
    });
}

function init_select2_surgery_name(init_data, ajax_url) {
    $('#id_surgery_name').select2({
        data: init_data,
        minimumInputLength: 3,
        tags: true,
        ajax: {
            delay: 500,
            url: ajax_url,
            data: function (params) {
                let query = {
                    name: params.term,
                };
                return query;
            },
            processResults: function (data) {
                return {
                    results: data.items
                }
            }
        }
    });
}

function init_select2_practice_code(init_data, ajax_url) {
    $('#id_practice_code').select2({
        data: init_data,
        minimumInputLength: 3,
        tags: true,
        ajax: {
            delay: 500,
            url: ajax_url,
            data: function (params) {
                let query = {
                    code: params.term,
                };
                return query;
            },
            processResults: function (data) {
                return {
                    results: data.items
                }
            }
        }
    });
}


function delay(callback, ms) {
  var timer = 0;
  return function() {
    var context = this, args = arguments;
    clearTimeout(timer);
    timer = setTimeout(function () {
      callback.apply(context, args);
    }, ms || 0);
  };
}
