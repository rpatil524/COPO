/**
 * Created by fshaw on 11/11/2016.
 */

$(document).ready(function () {



})

function setup_annotator(element){
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