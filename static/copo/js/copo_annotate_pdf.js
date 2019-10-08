// FS - 03/10/19
// For javascript relating to pdf annotations

$(document).ready(function () {
    // get latest list of ontologies from OLS
    get_ontologies_data()
    // setup and init Annotator
    var app = new annotator.App();
    app.include(annotator.ui.main, {
        element: document.getElementById("text-area"),
        editorExtensions: [
            // add ols_annotator which contains custom fields for the annotator window
            ols_annotator.getEditorExtension({defaultFields: false}),
            annotator.ui.tags.editorExtension
        ],
        viewerExtensions: [
            annotator.ui.tags.viewerExtension,
        ]
    });


    app.include(annotator.storage.http, {
        headers: {'X-CSRFToken': $.cookie('csrftoken')},
        prefix: '/copo'
    });

    var additional = function () {
        return {
            beforeAnnotationCreated: function (ann) {

            },
            annotationCreated: function(ann){
                refresh_text_annotations()
            },
            start: function (ann) {
            }
        };
    };
    app.include(annotator.ui.filter.standalone)
    app.include(additional)
    app.start().then(function () {
        var file_id = $("#file_id").val()
        app.annotations.load({"file_id": file_id});

    });

})


function get_ontologies_data() {
    $.ajax({
        url: '/rest/get_ontologies/',
        method: 'GET',
        dataType: 'json'
    }).done(function (d) {
        $(document).data("ontologies", d)
    })
}

