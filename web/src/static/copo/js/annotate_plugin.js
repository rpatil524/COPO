/**
 * Created by fshaw on 31/10/2016.
 */
Annotator.Plugin.StoreLogger = function (element) {
    return {
        pluginInit: function () {
            this.annotator
                .subscribe("annotationCreated", function (annotation) {
                    console.info("The annotation: %o has just been created!", annotation)
                })
                .subscribe("annotationUpdated", function (annotation) {
                    console.info("The annotation: %o has just been updated!", annotation)
                })
                .subscribe("annotationDeleted", function (annotation) {
                    console.info("The annotation: %o has just been deleted!", annotation)
                })
                .subscribe("annotationEditorShown", function (viewer, annotations) {
                    console.log(viewer)
                    var el = $(viewer.element).find('textarea')
                    $(viewer.element).find('textarea').attr('data-autocomplete', '/copo/ajax_search_ontology/')
                    AutoComplete({
                        selector:[
                            "textarea"
                        ]
                    })
                });
        }
    }
};
