$(document).ready(function () {


    var profileId = $('#profile_id').val();
    var wsprotocol = 'ws://';
    if (window.location.protocol == "https:") {
        wsprotocol = 'wss://';
    }
    var socket = new ReconnectingWebSocket(
        wsprotocol + window.location.host +
        '/ws/sample_status/' + profileId );
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
        alert(d.message)
    }


    $('#bbtn').on("click", function () {
        console.log("sending")
        socket.send(JSON.stringify({"message": "OBE"}))
    })


    function open_parse_modal() {
        $("#sample_spreadsheet_modal").modal("show")
    }


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


})

