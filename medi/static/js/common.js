function create_alert(message, level) {
    /**
     * @param {string} message: alert text
     * @param {string} level: alert type, choices are success, warning or error
    */
    let alert_class = 'alert-success';
    switch (level) {
        case 'success':
            alert_class = 'alert-success';
            break;
        case 'warning':
            alert_class = 'alert-warning';
            break;
        case 'error':
            alert_class = 'alert-danger';
            break;
    }

    let alert_html = '<div class="alert ' + alert_class + ' alert-dismissible" role="alert" id="alert-message">' +
        '<button type="button" class="close" data-dismiss="alert" aria-label="Close">' +
        '<span aria-hidden="true">&times;</span>' +
        '</button>' + message + '</div>';
    $('#alerts_block').html(alert_html)
}