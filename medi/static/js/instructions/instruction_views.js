var status = -1;
var cookieStatus;
var inst_statusDict = {}, gpuser_roleDict = {};
var clientuser_roleDict = {}, medidatauser_roleDict = {};
inst_statusDict["All"] = -1;
inst_statusDict["New"] = 0;
inst_statusDict["Redacting"] = 7;
inst_statusDict["In Progress"] = 1;
inst_statusDict["Completed"] = 2;
inst_statusDict["Rejected"] = 3;
inst_statusDict["Paid"] = 4;
inst_statusDict["Finalising"] = 5;
inst_statusDict["Rerun"] = 6;

gpuser_roleDict["All"] = -1;
gpuser_roleDict["GP Manager"] = 0;
gpuser_roleDict["GP"] = 1;
gpuser_roleDict["Other Practice Staff"] = 2;

clientuser_roleDict["All"] = -1;
clientuser_roleDict["Client Manager"] = 0;
clientuser_roleDict["Client Administrator"] = 1;

medidatauser_roleDict["Medidata"] = 0;

function filterGlobal () {
    $('#instructionsTable').DataTable().search(
        $('#search').val()
    ).draw();
}

function getUrlParameter(sParam) {
    var sPageURL = decodeURIComponent(window.location.search.substring(1)),
        sURLVariables = sPageURL.split('&'),
        sParameterName,
        i;

    for (i = 0; i < sURLVariables.length; i++) {
        sParameterName = sURLVariables[i].split('=');

        if (sParameterName[0] === sParam) {
            return sParameterName[1] === undefined ? true : sParameterName[1];
        }
    }
}

function getObjectKeyByValue(obj, val){
    for(var key in obj){
        if(obj[key] == val) return key;
    }
}

function gpuserStatusFilter(selected_status){
    window.location = '/accounts/view-users/?status=' + gpuser_roleDict[selected_status] + '&type=' + $('#filterUserType').val() + '&user_type=GP';
}

function mediuserStatusFilter(selected_status){
    window.location = '/accounts/view-users/?status=' + medidatauser_roleDict[selected_status] + '&type=' + $('#filterUserType').val() + '&user_type=MEDI';
}

function clientuserStatusFilter(selected_status){
    window.location = '/accounts/view-users/?status=' + clientuser_roleDict[selected_status] + '&type=' + $('#filterUserType').val() + '&user_type=CLT';
}

function userTypeFilter() {
    if(getUrlParameter('status')){
        status = getUrlParameter('status');
    }
    window.location = '/accounts/view-users/?status=' + status + '&type=' + $('#filterUserType').val();
}

function invoiceStatusFilter(selected_status){
    window.location = '/accounts/view-account/?status=' + inst_statusDict[selected_status];
}