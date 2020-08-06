function upload_spreadsheet(file) {
    var csrftoken = $.cookie('csrftoken');
    form = new FormData()
    form.append("file", file)
    jQuery.ajax({
        url: '/copo/sample_spreadsheet/',
        data: form,
        cache: false,
        contentType: false,
        processData: false,
        method: 'POST',
        type: 'POST', // For jQuery < 1.9
        headers: {"X-CSRFToken": csrftoken},

    }).error(function (data) {
        $("#upload_controls").fadeIn()
        console.log(data)
        BootstrapDialog.show({
            title: 'Error',
            message: "Error " + data.status + ": " + data.responseText
        });
    }).done(function (data) {
        console.log("WELL DONE")
        console.log(data)
    })
}

$(document).ready(function () {
    var profileId = $('#profile_id').val();
    var wsprotocol = 'ws://';
    var socket;
    if (window.location.protocol === "https:") {
        wsprotocol = 'wss://';
    }
    if (window.location.href.includes('/copo/accept_reject_sample/')) {
        socket = new WebSocket(
            wsprotocol + window.location.host +
            '/ws/dtol_status');
    } else {
        socket = new WebSocket(
            wsprotocol + window.location.host +
            '/ws/sample_status/' + profileId);
    }
    socket.onerror = function (e) {
        console.log("error ", e)
    }
    socket.onclose = function (e) {
        console.log("closing ", e)
    }
    socket.onopen = function (e) {
        console.log("opened ", e)
    }
    socket.onmessage = function (e) {
        console.log("received message ", e)
        d = JSON.parse(e.data)
        if (d.action === "close") {
            $("#" + d.html_id).fadeOut("50")
        } else if (d.action === "make_valid") {
            $("#" + d.html_id).html("Validated").removeClass("alert-info").addClass("alert-success")
        } else if (d.action === "info") {
            // check info div is visible
            if (!$("#" + d.html_id).is(":visible")) {
                $("#" + d.html_id).fadeIn("50")
            }
            $("#" + d.html_id).html(d.message)
            $("#spinner").fadeOut()
        } else if (d.action === "make_table") {
            var body = $("tbody")
            var count = 0
            for (r in d.message) {
                row = d.message[r]
                var tr = $("<tr/>")
                for (c in row) {

                    cell = row[c]
                    if (count === 0) {
                        var td = $("<th/>", {
                            "html": cell
                        })
                    } else {
                        var td = $("<td/>", {
                            "html": cell
                        })
                    }

                    tr.append(td)
                }
                if (count == 0) {
                    $("#sample_parse_table thead").append(tr)
                } else {
                    $("#sample_parse_table tbody").append(tr)
                }
                count++

            }
            $("#sample_info").hide()
            $("#sample_parse_table").DataTable({
                "scrollY": 400,
                "scrollX": true
            })
            $("#table_div").fadeIn(1000)
            $("#confirm_info").fadeIn(1000)
        }
    }
})


$(document).on("click", "#create_samples", function (event) {
    $.ajax({
        url: "/copo/create_spreadsheet_samples",

    }).done(function () {
        location.reload()
    }).error(function () {
        alert("something went wrong")
    })
})

$(document).on("click", ".new-samples-spreadsheet-template", function (event) {
    $("#sample_spreadsheet_modal").modal("show")
})






