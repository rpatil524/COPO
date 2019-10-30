$(document).ready(function () {

    //******************************Event Handlers Block*************************//
    var component = "publication";
    var copoFormsURL = "/copo/copo_forms/";
    var csrftoken = $.cookie('csrftoken');

    //get component metadata
    var componentMeta = get_component_meta(component);

    load_records(componentMeta); // call to load component records

    register_resolvers_event(); //register event for publication resolvers

    //instantiate/refresh tooltips
    refresh_tool_tips();

    //trigger refresh of table
    $('body').on('refreshtable', function (event) {
        do_render_component_table(globalDataBuffer, componentMeta);
    });

    //handle task button event
    $('body').on('addbuttonevents', function (event) {
        do_record_task(event);
    });

    //add new component button
    $(document).on("click", ".new-component-template", function (event) {
        do_record_task(event)
    });

    //details button hover
    $(document).on("mouseover", ".detail-hover-message", function (event) {
        $(this).prop('title', 'Click to view ' + component + ' details');
    });

    //******************************Functions Block******************************//


    function do_record_task(event) {

        BootstrapDialog.show({
            title: 'Create New Template',
            message: '<form id="template_name_form" role="form" data-toggle="validator">' +
                '<div class="form-group">\n' +
                '<label for="template_name">Template Name</label>\n' +
                '<input type="text" class="form-control" id="template_name" placeholder="" data-error="Template Name is Required" required>\n' +
                '<div class="help-block with-errors"></div>\n' +
                '</div>\n' +
                '</form>',
            onshow: function (dialog) {

            },
            buttons: [{
                label: 'Cancel',
                hotkey: 27, // Keycode of esc
                action: function (dialogRef) {
                    dialogRef.close()
                }
            }, {
                label: 'Create',
                hotkey: 13,
                action: function (dialogRef) {
                    $("#template_name_form").validator("validate")
                    var template_name = $(dialogRef.$modalContent).find("#template_name").val()
                    if (template_name) {
                        $.ajax({
                                url: "/copo/new_metadata_template/",
                                data: {"template_name": template_name},
                                type: "GET"
                            }
                        ).done(function(data){
                            dialogRef.close()
                            window.location = data
                        })

                    }
                }
            }]
        });
        /*

        var task = event.task.toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
        var tableID = event.tableID; //get target table

        //retrieve target records and execute task
        var table = $('#' + tableID).DataTable();
        var records = []; //
        $.map(table.rows('.selected').data(), function (item) {
            records.push(item);
        });

        //add task
        if (task == "add") {

        }


        //edit task
        if (task == "edit") {
            $.ajax({
                url: copoFormsURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'task': 'form',
                    'component': component,
                    'target_id': records[0].record_id //only allowing row action for edit, hence first record taken as target
                },
                success: function (data) {
                    json2HtmlForm(data);
                },
                error: function () {
                    alert("Couldn't build publication form!");
                }
            });
        }

        //table.rows().deselect(); //deselect all rows

         */
    }


})//end document ready