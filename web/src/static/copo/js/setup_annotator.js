/**
 * Created by fshaw on 11/11/2016.
 */

$(document).ready(function () {

    $(document).data('annotator', true)

    $(document).ajaxStart(function () {
        $('#processing_div').show()
    })
    $(document).ajaxStop(function () {
        $('#processing_div').hide()
    })


    $('#processing_div').hide()
    $('#file_picker_modal').modal('show')
    $("#form_submit_btn").on('click', function () {
        var formData = new FormData();
        formData.append('file', $('#InputFile')[0].files[0]);
        var csrftoken = $.cookie('csrftoken');
        var url = "/api/upload_annotation_file/"
        $.ajax({
            url: url,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: formData,
            processData: false,
            contentType: false,
            dataType: 'json'
        }).done(function (e) {
            $('#annotation_content').html(e.html)
            $.cookie('document_name', e.doc_name, {expires: 1, path: '/',});
            setup_annotator()
            $('#file_picker_modal').modal('hide')
        });
    })
})

function setup_annotator(element) {
    // setup cookie to store uri for annotation


    // setup csrf token and annotator plugins
    var csrftoken = $.cookie('csrftoken');
    var app = new annotator.App();
    app.include(annotator.ui.main)
    app.include(annotator.storage.http, {
        prefix: 'http://127.0.0.1:8000/api',
        headers: {
            'X-CSRFToken': csrftoken,
        },
    });
    app.start().then(function () {
        app.annotations.load();
    });

    // attach data parameter stating that this page is using annotator, therefore what autocomplete should do
    $(this).data('annotator', true)
}