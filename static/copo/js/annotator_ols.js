var ols_annotator = {

    // start: function (app) {
    //     app.notify("Hello, world!");
    //
    // },

    getEditorExtension: function getEditorExtension(options) {


        return function editorExtension(editor) {

            this.constructor = function (options) {
                //options.defaultFields = false;
                //Widget.call(this, options);
            }


            editor.addField({
                type: "input",
                label: "OLS Searchbox",
                id: "search_term_text_box",
                load: function(field, annotation){

                }
            })
            editor.addField({
                type: "div",
                id: "search_results",
                submit: function(field, annotation) {
                    annotation.ols_string = $(field).html()

                }
            })

        };
    }

}

