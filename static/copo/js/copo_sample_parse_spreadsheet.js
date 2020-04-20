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
        success: function (data) {
            alert(data);
        }
    }).error(function(data){
        console.error("BIG FUCKING MISTAKE CUNTFACE")
        console.error(data)
    }).done(function(data) {
        console.log("WELL DONE")
        console.log(data)
    })
}