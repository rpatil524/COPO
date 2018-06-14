$(document).ready(function () {

    //******************************Event Handlers Block*************************//
    var component = "repository";
    var copoFormsURL = "/copo/copo_forms/";
    var csrftoken = $.cookie('csrftoken');

    //get component metadata
    var componentMeta = get_component_meta(component);

    load_records(componentMeta); // call to load component records

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
        initiate_form_call(component)

    });

    $('body').on('postformload', function (event) {
        disable_username_password_boxes()
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

            return false;
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
    }


    $(document).on('change', '#copo\\.repository\\.type', function (e) {
        var type = $(e.currentTarget).val()
        enable_authentication_boxes()
        if (type == 'dspace') {
            disable_apikey_box()
        }
        else {
            disable_username_password_boxes()
        }
    })

    function disable_username_password_boxes() {
        $('#copo\\.repository\\.username').attr('disabled', 'disabled')
        $('#copo\\.repository\\.password').attr('disabled', 'disabled')
    }

    function disable_apikey_box() {
        $('#copo\\.repository\\.apikey').attr('disabled', 'disabled')
    }

    function enable_authentication_boxes() {
        $('#copo\\.repository\\.apikey').removeAttr('disabled')
        $('#copo\\.repository\\.username').removeAttr('disabled')
        $('#copo\\.repository\\.password').removeAttr('disabled')
    }

})//end document ready

