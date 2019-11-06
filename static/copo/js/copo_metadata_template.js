$(document).ready(function () {
    $(document).on("click", ".update_title_button", function (event) {



        $(".new_title_div").addClass("loading")
        var title = $('#new_title').val()
        var template_id = $('#template_id').val()
        if (title) {
            $.ajax({
                    url: "/copo/update_metadata_template_name/",
                    data: {"template_name": title, "template_id": template_id},
                    type: "GET"
                }
            ).done(function (data) {
                $('#new_title').val("")
                $('#new_title').attr("placeholder", data)
                $(".new_title_div").removeClass("loading")
            })
        } else {
            $(".new_title_div").removeClass("loading")
        }

    })
    //******************************Event Handlers Block*************************//
    var component = "metadata_template";
    var copoFormsURL = "/copo/copo_forms/";
    var csrftoken = $.cookie('csrftoken');

    //get component metadata
    var componentMeta = get_component_meta(component);

    load_records(componentMeta); // call to load component records

    //register_resolvers_event(); //register event for publication resolvers

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
                            ).done(function (data) {
                                dialogRef.close()
                                window.location = data
                            })

                        }
                    }
                }]
            });

        }

        if (task == "delete") {
            alert("implement delete")
        }
        //edit task
        if (task == "edit") {
            window.location = "/copo/author_template/" + records[0].record_id + "/view"
        }

        //table.rows().deselect(); //deselect all rows


    }


    $("#template_content").droppable({
        drop: function (event, ui) {
            var d = ui.draggable[0]
            $(d).css("width", "50%").css("margin", "30px 0 0 30px")
            $(this).append(ui.draggable[0]);
        }
        //activeClass: "dropActive",
        //tolerance: "pointer",
        // drop: metadata_drop_handler,
        //accept:".annotation_term"
    }).sortable({

    })

    function metadata_drop_handler(ev, ui) {

        var data = new Object();
        var iri = $(ui.draggable.context).data("iri")
        data.label = $(ui.draggable.context).data("label")
        data.id = $(ui.draggable.context).data("id")
        data.obo_id = $(ui.draggable.context).data("obo_id")
        data.ontology_name = $(ui.draggable.context).data("ontology_name")
        data.ontology_prefix = $(ui.draggable.context).data("ontology_prefix")
        data.short_form = $(ui.draggable.context).data("short_form")
        data.type = $(ui.draggable.context).data("type")
        data.description = $(ui.draggable.context).data("description")
    }

})//end document ready

