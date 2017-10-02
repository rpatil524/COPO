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
        handle_pub_add();
    });

    //details button hover
    $(document).on("mouseover", ".detail-hover-message", function (event) {
        $(this).prop('title', 'Click to view ' + component + ' details');
    });

    //******************************Functions Block******************************//

    function handle_pub_add() {
        $("#pub_options").collapse("toggle");
    }

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
            handle_pub_add();
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


        // var task = elem.attr('data-record-action').toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
        // var taskTarget = elem.attr('data-action-target'); //is the task targeting a single 'row' or group of 'rows'?
        //
        // var ids = [];
        //
        // if (taskTarget == 'row') {
        //     ids = [elem.attr('data-record-id')];
        // } else if (taskTarget == 'rows') {
        //     //get reference to table, and retrieve selected rows
        //     if ($.fn.dataTable.isDataTable('#' + tableID)) {
        //         var table = $('#' + tableID).DataTable();
        //
        //         ids = $.map(table.rows('.selected').data(), function (item) {
        //             return item[item.length - 1];
        //         });
        //     }
        // }
        //
        // //handle button actions
        // if (ids.length > 0) {
        //     if (task == "edit") {
        //         $.ajax({
        //             url: copoFormsURL,
        //             type: "POST",
        //             headers: {'X-CSRFToken': csrftoken},
        //             data: {
        //                 'task': 'form',
        //                 'component': component,
        //                 'target_id': ids[0] //only allowing row action for edit, hence first record taken as target
        //             },
        //             success: function (data) {
        //                 json2HtmlForm(data);
        //             },
        //             error: function () {
        //                 alert("Couldn't build publication form!");
        //             }
        //         });
        //     } else if (task == "delete") { //handles delete, allows multiple row delete
        //         var deleteParams = {component: component, target_ids: ids};
        //         do_component_delete_confirmation(deleteParams);
        //     }
        // }
    }


    function register_resolvers_event() {
        //event handler for resolving doi and pubmed
        $('.resolver-submit').on('click', function (event) {
            var triggerElem = $(this);
            $(this).html("<div style='text-align: center'><i class='fa fa-spinner fa-pulse'></i></div>");

            var elem = $(this).closest(".input-group").find(".resolver-data");
            var idHandle = elem.val();

            //reset input field to placeholder
            elem.val("");

            idHandle = idHandle.replace(/^\s+|\s+$/g, '');

            var idType = elem.attr("data-resolver");

            if (idHandle.length == 0) {
                var alertMessage = "Please supply a value for PubMed ID before clicking the 'Resolve' button!";

                if (idType == "doi") {
                    alertMessage = "Please supply a value for DOI before clicking the 'Resolve' button!";
                }

                display_copo_alert("warning", alertMessage, 10000);

                triggerElem.html("Resolve");
                return false;
            }

            $.ajax({
                url: copoFormsURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'task': 'doi',
                    'component': component,
                    'id_handle': idHandle,
                    'id_type': idType
                },
                success: function (data) {
                    json2HtmlForm(data);
                    triggerElem.html("Resolve");
                    $("#pub_options").collapse("hide");
                },
                error: function () {
                    triggerElem.html("Resolve");
                    $("#pub_options").collapse("hide");
                    alert("Couldn't resolve resource!");
                }
            });
        });
    }

})//end document ready

