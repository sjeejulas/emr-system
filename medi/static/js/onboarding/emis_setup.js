
function copyToClipboard(text, el) {
    var copyTest = document.queryCommandSupported("copy");
    var elOriginalText = el.attr("data-original-title");

    if (copyTest === true) {
        var copyTextArea = document.createElement("textarea");
        copyTextArea.value = text;
        document.body.appendChild(copyTextArea);
        copyTextArea.select();
        try {
            var successful = document.execCommand("copy");
            var msg = successful ? "Copied!" : "Whoops, not copied!";
            el.attr("data-original-title", msg).tooltip("show");
        } catch (err) {

        }
        document.body.removeChild(copyTextArea);
        el.attr("data-original-title", elOriginalText);
    } else {
        window.prompt("Copy to clipboard: Ctrl+C or Command+C, Enter", text);
    }
}


function pollingEmis(url) {
    $("#checkingEmisButton").addClass("pendingCheck");
    $("#checkingEmisButton").html(
        "<img src='/static/images/emis_setup/Spin-1s-40px.gif' style='height: 50px; width: 50px;'/> Authenticating..."
    );
    setTimeout(function () {
        $.ajax({
            url: url,
            success: function (data) {
                if(data["status"] >= 200 && data["status"] < 400) {
                    $(".btn-checkSetup").hide();
                    $(".emisSetupSuccess").removeClass("d-none");
                    setTimeout(function () {
                        document.location.href = "/accounts/login/";
                    }, 2000)
                } else {
                    $('#checkingEmisButton').prop("disabled", false);
                    $("#checkingEmisButton").removeClass("pendingCheck");
                    $("#checkingEmisButton").html("<i class='fas fa-question'></i>&nbsp; Check Setup");
                    $("#failSetupEmisModal").modal({
                        backdrop: "static"
                    });
                }
            },
        });
    }, 2000);
}

function pollingNewEmis(url) {
    $("#checkingEmisButton").addClass("pendingCheck");
    $("#checkingEmisButton").html(
        "<img src='/static/images/emis_setup/Spin-1s-40px.gif' style='height: 20px; width: 20px;'/> Authenticating..."
    );
    setTimeout(function () {
        $.ajax({
            url: url,
            success: function (data) {
                if(data["status"] >= 200 && data["status"] < 400) {
                    $(".btn-checkChangeSetup").hide();
                    $(".emisSetupSuccess").removeClass("d-none");
                    setTimeout(function () {

                    }, 2000)
                } else {
                    $(".emisSetupFail").removeClass("d-none");
                    $('#checkingEmisButton').prop("disabled", false);
                    $("#checkingEmisButton").removeClass("pendingCheck");
                    $("#checkingEmisButton").html("<i class='fas fa-question'></i>&nbsp; Check Setup");
                }
            },
        });
    }, 2000);
}

function validateBTN( progressPercent ) {
    if( progressPercent == 20 || progressPercent == 55 || progressPercent == 67 ){
        $('#backBTN').prop('disabled',true);
    } else {
        $('#backBTN').prop('disabled',false);
    }
    
    if (progressPercent == 43) {
        $('#username-block').show();
    }
    if( progressPercent == 51 || progressPercent == 63 || progressPercent == 83 ){
        $('#nextBTN').prop('disabled',true);
        $('#completeBTN').prop('disabled',false);
    } else {
        $('#nextBTN').prop('disabled',false);
        $('#completeBTN').prop('disabled',true);
    }
}

function fromReload() {
    $('#id_label').removeClass('text-danger');
    $('#progress_bar').removeClass('bg-danger');

    $('#id_label').addClass('text-success');
    $('#progress_bar').addClass('bg-success');

    $('#progress_percent').text('87%');
    $('#progress_bar').attr('aria-valuenow', '87');
    $('#progress_bar').css('width', '87%');

    picPath = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2020.jpg';
    titleCaption = 'e) If you have RBAC roles in your surgery, please ensure you add "Mr emr emr" and assign him as "Clinical Practitioner Access Role"';
    $('#setup-min-pic').attr('href', picPath );
    $('#setup-full-pic').attr('src', picPath );
    $('#setup-caption').text( titleCaption );
    $('#username-block').show();

    $('#step2-block').show();
    picPath = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2011.png';
    titleCaption = 'h) Click "Activate Application" at the top';
    $('#setup-min-pic_2').attr('href', picPath );
    $('#setup-full-pic_2').attr('src', picPath );
    $('#setup-caption_2').text( titleCaption );

    $('#step3-block').show();
    picPath = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2017.jpg';
    titleCaption = 'm) Find the new user you created and tick the boxes to the right of it';
    $('#setup-min-pic_3').attr('href', picPath );
    $('#setup-full-pic_3').attr('src', picPath );
    $('#setup-caption_3').text( titleCaption );

    $('#step4-block').show();
    $('#main-btn-block').hide();
    $('#secon-btn-block').show();
}

function changeAttr( status ) {
    var picPath, titleCaption;
    var percent = parseInt( $('#progress_bar').attr('aria-valuenow') );
    var aCaption = 'a) Menu > Configuration > Organisation Configuration',
        bCaption = 'b) Click the "Add" button, select "New user"',
        cCaption = 'c) Enter user details as "Mr emr emr" Enter password "emr and then your EMIScode" and paste in your password you copied from the clip board',
        dCaption = 'd) Now you need to assign the correct role for your user. Give "emr emr" the role of "General Medical Practitioner". For the "User Mnemonic" add in your emr+EMIScode as before.',
        eCaption = 'e) If you have RBAC roles in your surgery, please ensure you add "Mr emr emr" and assign him as "Clinical Practitioner Access Role"',
        fCaption = 'f) Menu > System Tools > EMAS Manager',
        gCaption = 'g) Select "Partner API" at the bottom',
        hCaption = 'h) Click "Activate Application" at the top',
        iCaption = 'i) Click "Edits Users" button',
        jCaption = 'j) Find the new user you created and tick the box next to it',
        kCaption = 'k) You’ll be asked to enter that password again. Click ok. Then ok again.',
        lCaption = 'l) Click "Login Access" button',
        mCaption = 'm) Find the new user you created and tick the boxes to the right of it',
        aPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2002.png',
        bPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2003.png',
        cPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2004.jpg',
        dPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2019.jpg',
        ePic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2020.jpg',
        fPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2008.png',
        gPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2009.png',
        hPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2011.png',
        iPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2012.png',
        jPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2013.jpg',
        kPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2014.jpg',
        lPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2016.png',
        mPic = '/static/images/emis_setup/Medidata%20-%20Activating%20in%20EMIS%2017.jpg';
    switch( percent ) {
        // Step 1 Control.
        case 35:
            if( status == 'next' ) {
                $('#setup-min-pic').attr('href', bPic );
                $('#setup-full-pic').attr('src', bPic );
                $('#setup-caption').text( bCaption );
            }
            break;
        case 39:
            if( status == 'next' ){
                $('#setup-min-pic').attr('href', cPic );
                $('#setup-full-pic').attr('src', cPic );
                $('#setup-caption').text( cCaption );
            } else {
                $('#setup-min-pic').attr('href', aPic );
                $('#setup-full-pic').attr('src', aPic );
                $('#setup-caption').text( aCaption );
            }
            break;
        case 43:
            if( status == 'next' ){
                $('#setup-min-pic').attr('href', dPic );
                $('#setup-full-pic').attr('src', dPic );
                $('#setup-caption').text( dCaption );
            } else {
                $('#setup-min-pic').attr('href', bPic );
                $('#setup-full-pic').attr('src', bPic );
                $('#setup-caption').text( bCaption );
            }
            break;
        case 47:
            if( status == 'next' ){
                $('#setup-min-pic').attr('href', ePic );
                $('#setup-full-pic').attr('src', ePic );
                $('#setup-caption').text( eCaption );
            } else {
                $('#setup-min-pic').attr('href', cPic );
                $('#setup-full-pic').attr('src', cPic );
                $('#setup-caption').text( cCaption );
            }
            break;
        case 51:
            if (status == 'back') {
                $('#setup-min-pic').attr('href', dPic );
                $('#setup-full-pic').attr('src', dPic );
                $('#setup-caption').text( dCaption );
            }
            break;
        // Step 2 Control.
        case 55:
            if( status == 'next' ){
                $('#setup-min-pic_2').attr('href', gPic );
                $('#setup-full-pic_2').attr('src', gPic );
                $('#setup-caption_2').text( gCaption );
            }
            break;
        case 59:
            if( status == 'next' ){
                $('#setup-min-pic_2').attr('href', hPic );
                $('#setup-full-pic_2').attr('src', hPic );
                $('#setup-caption_2').text( hCaption );
            } else {
                $('#setup-min-pic_2').attr('href', fPic );
                $('#setup-full-pic_2').attr('src', fPic );
                $('#setup-caption_2').text( fCaption );
            }
            break;
        case 63:
            if (status == 'back') {
                $('#setup-min-pic_2').attr('href', gPic );
                $('#setup-full-pic_2').attr('src', gPic );
                $('#setup-caption_2').text( gCaption );
            }
            break;
        // Step 3 control.
        case 67:
            if( status == 'next' ){
                $('#setup-min-pic_3').attr('href', jPic );
                $('#setup-full-pic_3').attr('src', jPic );
                $('#setup-caption_3').text( jCaption );
            }
            break;
        case 71:
            if( status == 'next' ){
                $('#setup-min-pic_3').attr('href', kPic );
                $('#setup-full-pic_3').attr('src', kPic );
                $('#setup-caption_3').text( kCaption );
            } else {
                $('#setup-min-pic_3').attr('href', iPic );
                $('#setup-full-pic_3').attr('src', iPic );
                $('#setup-caption_3').text( iCaption );
            }
            break;
        case 75:
            if( status == 'next' ){
                $('#setup-min-pic_3').attr('href', lPic );
                $('#setup-full-pic_3').attr('src', lPic );
                $('#setup-caption_3').text( lCaption );
            } else {
                $('#setup-min-pic_3').attr('href', jPic );
                $('#setup-full-pic_3').attr('src', jPic );
                $('#setup-caption_3').text( jCaption );
            }
            break;
        case 79:
            if( status == 'next' ){
                $('#setup-min-pic_3').attr('href', mPic );
                $('#setup-full-pic_3').attr('src', mPic );
                $('#setup-caption_3').text( mCaption );
            } else {
                $('#setup-min-pic_3').attr('href', kPic );
                $('#setup-full-pic_3').attr('src', kPic );
                $('#setup-caption_3').text( kCaption );
            }
            break;
        case 83:
            if( status == 'back' ){
                $('#setup-min-pic_3').attr('href', lPic );
                $('#setup-full-pic_3').attr('src', lPic );
                $('#setup-caption_3').text( lCaption );
            }
            break;
    }

    if (status == 'next') {
        percent = percent + 4;
    } else {
        if (percent == 35)
            return;
        percent = percent - 4;
    }
    $('#progress_percent').text( percent + ' % ');
    $('#progress_bar').attr('aria-valuenow', percent);
    $('#progress_bar').css('width', percent + '%');

    validateBTN($('#progress_bar').attr('aria-valuenow'));
}