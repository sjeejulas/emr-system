(function ($) {
    $(document).ready(function () {
        $("#id_max_day_lvl_4").prop( "disabled", true );
        $("#id_max_day_lvl_4").val(parseInt($('#id_max_day_lvl_3').val()) +1);
        $('#id_max_day_lvl_3').on('change', function () {
            let max_day_lvl_3 = parseInt($('#id_max_day_lvl_3').val()) +1;
            $('#id_max_day_lvl_4').val(max_day_lvl_3);
        });
    });
})(django.jQuery);