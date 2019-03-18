$(document).ready(function () {

    $("#frm_login_submit").on('click', function () {
        //frm_login_submit_callback($(this));
    });

    $("#btn_orcid").on('click', orcid_btn_handler)


});

function frm_login_submit_callback(request) {

    //add ajax query to get orchid stuff
    //get username and pasword
    var username = $("#frm_login_username").val();
    var password = $("#frm_login_password").val();

    if ((username) && (password)) {

        $.ajax({
            type: "POST",
            url: "?xhr",
            data: {
                'username': username,
                'password': password
            },
            success: function (data) {

                //results = $(data).find('#results').html()
                alert(data);

            },
            error: function () {
                alert("Error");
            }
        })
    }
}

function orcid_btn_handler(e) {
    e.preventDefault();
    $.ajax({
        type: "GET",
        url: "/api/check_orcid_credentials/",
        dataType: "json"
    }).done(function (data) {
        // if creds invalid, prompt user
        if (data.exists == false) {
            url = data.authorise_url;
            window.location.href = url;
        }
    })

}