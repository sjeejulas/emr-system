(function($) {
    function diaplayCreateUserInformation(typeUser, titlePage){
        if( titlePage == "Add user | MediData administration" ) {
            if(typeUser == "Medidata"){
                $('#medidatauser-group').show();
                $('#clientuser-group').hide();
                $('#generalpracticeuser-group').hide();
            } else if(typeUser == "Client") {
                $('#medidatauser-group').hide();
                $('#clientuser-group').show();
                $('#generalpracticeuser-group').hide();
            } else if(typeUser == "General") {
                $('#medidatauser-group').hide();
                $('#clientuser-group').hide();
                $('#generalpracticeuser-group').show();
            } else {
                $('#medidatauser-group').hide();
                $('#clientuser-group').hide();
                $('#generalpracticeuser-group').hide();
            }
        } else {
            $('#medidatauser-group').show();
            $('#clientuser-group').show();
            $('#generalpracticeuser-group').show();
        }
    }

    $(document).ready(function() {
        var titlePage = $(document).attr('title');
        diaplayCreateUserInformation(($('#id_type option:selected').text()).split(' ')[0], titlePage);

        $('#id_type').on('change',function() {
            var selected = ($('#id_type option:selected').text()).split(' ')[0];
            diaplayCreateUserInformation(selected, titlePage);
        });
    });
})(django.jQuery);