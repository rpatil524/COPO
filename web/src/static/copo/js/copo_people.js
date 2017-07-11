/**
 * Created by etuka on 06/11/15.
 */

$(document).ready(function () {

    //******************************Event Handlers Block*************************//

    // get table data to display via the DataTables API
    var tableID = null;
    var component = "person";
    var copoFormsURL = "/copo/copo_forms/";
    var copoVisualsURL = "/copo/copo_visualize/";

    csrftoken = $.cookie('csrftoken');

    //global_help_call
    do_global_help(component);

    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {'X-CSRFToken': csrftoken},
        data: {
            'task': 'table_data',
            'component': component
        },
        success: function (data) {
            do_render_table(data);
        },
        error: function () {
            alert("Couldn't retrieve "+component+" data!");
        }
    });

    // handle/attach events to table buttons
    $('body').on('addbuttonevents', function (event) {
        tableID = event.tableID;

        $(document).on("click", ".copo-dt", function (event) {
            do_record_task($(this));
        });

    });

    //instantiate/refresh tooltips
    refresh_tool_tips();


    //******************************Functions Block******************************//

    function do_record_task(elem) {
        var task = elem.attr('data-record-action').toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
        var taskTarget = elem.attr('data-action-target'); //is the task targeting a single 'row' or group of 'rows'?

        var ids = [];

        if (taskTarget == 'row') {
            ids = [elem.attr('data-record-id')];
        } else if (taskTarget == 'rows') {
            //get reference to table, and retrieve selected rows
            if ($.fn.dataTable.isDataTable('#' + tableID)) {
                var table = $('#' + tableID).DataTable();

                ids = $.map(table.rows('.selected').data(), function (item) {
                    return item[item.length - 1];
                });
            }
        }

        //handle button actions
        if (ids.length > 0) {
            if (task == "edit") {
                $.ajax({
                    url: copoFormsURL,
                    type: "POST",
                    headers: {'X-CSRFToken': csrftoken},
                    data: {
                        'task': 'form',
                        'component': component,
                        'target_id': ids[0] //only allowing row action for edit, hence first record taken as target
                    },
                    success: function (data) {
                        json2HtmlForm(data);
                    },
                    error: function () {
                        alert("Couldn't build "+component+" form!");
                    }
                });
            } else if (task == "delete") { //handles delete, allows multiple row delete
                var deleteParams = {component: component, target_ids: ids};
                do_component_delete_confirmation(deleteParams);
            }
        }

    }

});

