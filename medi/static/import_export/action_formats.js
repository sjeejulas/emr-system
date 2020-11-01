(function($) {
    $(document).ready(function() {
        var $actionsSelect, $formatsElement;

        if ($('body').hasClass('grp-change-list')) {
            $actionsSelect = $('#grp-changelist-form select[name="action"]');
            $formatsElement = $('#grp-changelist-form select[name="file_format"]');
        } else {
            $actionsSelect = $('#changelist-form select[name="action"]');
            $formatsElement = $('#changelist-form select[name="file_format"]').parent();
        }

        $actionsSelect.on('change', function() {
            if ($(this).val() === 'export_admin_action') {
                $formatsElement.show();
            } else {
                $formatsElement.hide();
            }
        });

        $actionsSelect.change();

        $('.export_link').on('click', function(e) {
            e.preventDefault();
            $('select[name="action"]').val('export_admin_action');
            $('select[name="file_format"]').val('0');
            $('button[name="index"]').val('0');

            setTimeout(function() {
                window.location.reload();
            }, 500);

            $('#changelist-form').submit();
        });
    });
})(django.jQuery);