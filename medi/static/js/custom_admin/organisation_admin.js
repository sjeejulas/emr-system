(function($) {
    function diaplayAdditionInformation(organisationType){
        if(organisationType == "Insurance" || organisationType == "Medicolegal"){
            $('.additionInfo').show();
            $('.Insurance').show();
            $('.ConsentType').show();
        } else {
            $('.additionInfo').hide();
            $('.Insurance').hide();
            $('.ConsentType').hide();
        }
    }

    $(document).ready(function() {
        diaplayAdditionInformation(($('#id_type option:selected').text()).split(' ')[0]);

        $('#id_type').on('change',function() {
            var selected = ($('#id_type option:selected').text()).split(' ')[0];
            diaplayAdditionInformation(selected);
        });
    });
})(django.jQuery);