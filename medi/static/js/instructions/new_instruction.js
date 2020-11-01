function reformatted_date(formatted_date){
    let splitted = formatted_date.split('/');
    let day = splitted[0];
    let month = splitted[1];
    let year = splitted[2];

    return month + '/' + day + '/' + year;
}