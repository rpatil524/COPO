//**some re-usable functions across different modules
var copoFormsURL = "/copo/copo_forms/";
var copoVisualsURL = "/copo/copo_visualize/";

$(document).ready(function () {

    //dismiss alert
    $(document).on("click", ".alertdismissOK", function () {
        WebuiPopovers.hideAll();
    });

});

function set_empty_component_message(dataRows) {
    //decides, based on presence of record, to display table or getting started info

    if (dataRows.length == 0) {
        if ($(".table-parent-div").length) {
            $(".table-parent-div").hide();
        }

        if ($(".page-welcome-message").length) {
            $(".page-welcome-message").show();
        }

    } else {
        if ($(".table-parent-div").length) {
            $(".table-parent-div").show();
        }

        if ($(".page-welcome-message").length) {
            $(".page-welcome-message").hide();
        }
    }
}

function place_task_buttons(componentMeta) {
    //place custom buttons on table

    if (!componentMeta.recordActions.length) {
        return;
    }

    var table = $('#' + componentMeta.tableID).DataTable();

    var customButtons = $('<span/>', {
        style: "padding-left: 15px;",
        class: "copo-table-cbuttons"
    });

    $(table.buttons().container()).append(customButtons);


    componentMeta.recordActions.forEach(function (item) {
        var actionBTN = $(".record-action-templates").find("." + item).clone();
        actionBTN.removeClass(item);
        actionBTN.attr("data-table", componentMeta.tableID);
        customButtons.append(actionBTN);
    });

    refresh_tool_tips();

    //table action buttons
    do_table_buttons_events();
}

function do_crud_action_feedback(meta) {
    //feedback to the user on CRUD actions
    display_copo_alert(meta.status, meta.message, 20000);
}

function do_table_buttons_events() {
    //attaches events to table buttons

    $(document).on("click", ".copo-dt", function (event) {
        event.preventDefault();

        $('.copo-dt').webuiPopover('destroy');


        var elem = $(this);
        var task = elem.attr('data-action').toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
        var tableID = elem.attr('data-table'); //get target table
        var btntype = elem.attr('data-btntype'); //type of button: single, multi, all
        var title = elem.find(".action-label").html();
        var message = elem.attr("data-error-message");

        if (!message) {
            message = "No records selected for " + title + " action"
        }

        //validate event before passing to handler
        var table = $('#' + tableID).DataTable();
        var selectedRows = table.rows({
            selected: true
        }).count(); //number of rows selected

        var triggerEvent = true;

        //do button type validation based on the number of records selected
        if (btntype == "single" || btntype == "multi") {
            if (selectedRows == 0) {
                triggerEvent = false;
            } else if (selectedRows > 1 && btntype == "single") { //sort out 'single record buttons'
                triggerEvent = false;
            }

        }

        if (triggerEvent) { //trigger button event, else deal with error
            var event = jQuery.Event("addbuttonevents");
            event.tableID = tableID;
            event.task = task;
            event.title = title;
            $('body').trigger(event);
        } else {
            //alert user

            BootstrapDialog.show({
                title: "Record action",
                message: message,
                cssClass: 'copo-modal3',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_WARNING,
                buttons: [{
                    label: 'OK',
                    cssClass: 'tiny ui basic orange button',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                }]
            });


        }

    });
}


function display_copo_alert(alertType, alertMessage, displayDuration) {
    //function displays alert or info to the user
    //alertType:  'success', 'warning', 'info', 'danger' - modelled after bootstrap alert classes
    //alertMessage: the actual message to be displayed to the user
    //displayDuration: how long should the alert be displayed for before taking it down

    var infoPanelElement = $("#page_alert_panel");

    if (infoPanelElement.length) {
        //reveal tab if not already shown
        $('.copo-sidebar-tabs a[href="#copo-sidebar-info"]').tab('show');

        var alertElement = $(".alert-templates").find(".alert-" + alertType).clone();
        alertElement.find(".alert-message").html(alertMessage);

        infoPanelElement.prepend(alertElement);

        // setTimeout(function () {
        //     alertElement.removeClass("alert-" + alertType);
        //     alertElement.find(".alert-message").css("color", "#ededed");
        // }, displayDuration);
    }

}

function deselect_records(tableID) {
    var table = $('#' + tableID).DataTable();
    table.rows().deselect();
}

function do_render_component_table(data, componentMeta) {
    var tableID = componentMeta.tableID;
    var dataSet = data.table_data.dataSet;
    var cols = data.table_data.columns;
    var visibleColumns = 10000; //a very high number of columns to display as upper limit

    if (componentMeta.visibleColumns) {
        visibleColumns = componentMeta.visibleColumns;
    }

    set_empty_component_message(dataSet); //display empty component message for potential first time users

    if (dataSet.length == 0) {
        return false;
    }

    // treat columns
    var columns = [{
        "className": 'summary-details-control detail-hover-message',
        "orderable": false,
        "data": null,
        "title": "Details",
        "defaultContent": ''
    }];

    var columnDefs = [{
        "width": "5%",
        "targets": 0
    }]

    //add extra column, if datafile component, for displaying metadata rating
    if (componentMeta.component == "datafile") {

        columns.push({
            "orderable": false,
            "data": null,
            "className": "describe-status",
            "title": "",
            "defaultContent": '<span style="cursor: pointer;" class="metadata-rating uncertain"><i class="fa fa-square" aria-hidden="true"></i></span>'
        });

        columnDefs.push({
            "width": "1%",
            "targets": 1
        });
    }

    var sortIndex = 1; //column by which records may be sorted

    for (var i = 0; i < cols.length; ++i) {
        var col = cols[i];
        col["visible"] = false;

        // use date_modified as sort column
        if (col.data == "date_modified") {
            sortIndex = i + 1;
        }

        //only display the specified number of columns and the 'date_modifed' column, all others go in a sub-table

        if ((i < visibleColumns) || col.data == "date_modified") {
            col["visible"] = true;
            col["render"] = function (data, type, row, meta) {
                var collapseLink = row.record_id + "_" + meta.col;

                return $('<div></div>').append(deconvulate_column_data(data, collapseLink)).html();
            }
        }

        columns.push(col);
    }

    //set data
    var table = null;

    if ($.fn.dataTable.isDataTable('#' + tableID)) {
        //if table instance already exists, then do refresh
        table = $('#' + tableID).DataTable();
    }

    if (table) {
        //clear old, set new data
        table.rows().deselect();
        table
            .clear()
            .draw();
        table
            .rows
            .add(dataSet);
        table
            .columns
            .adjust()
            .draw();
        table
            .search('')
            .columns()
            .search('')
            .draw();
    } else {
        table = $('#' + tableID).DataTable({
            data: dataSet,
            searchHighlight: true,
            ordering: true,
            lengthChange: true,
            buttons: [
                'selectAll',
                'selectNone'
            ],
            select: {
                style: 'multi',
            },
            language: {
                "info": "Showing _START_ to _END_ of _TOTAL_ records",
                "search": " ",
                "lengthMenu": "show _MENU_ records",
                select: {
                    rows: {
                        _: "%d records selected",
                        0: "<span class='extra-table-info'>Click <span class='fa-stack' style='color:green; font-size:10px;'><i class='fa fa-circle fa-stack-2x'></i><i class='fa fa-plus fa-stack-1x fa-inverse'></i></span> beside a record to view details</span>",
                        1: "%d record selected"
                    }
                },
                buttons: {
                    selectAll: "Select all",
                    selectNone: "Select none"
                }
            },
            order: [
                [sortIndex, "desc"]
            ],
            columns: columns,
            columnDefs: columnDefs,
            fnDrawCallback: function () {
                refresh_tool_tips();
                refresh_sub_table(componentMeta, columns);
                var event = jQuery.Event("posttablerefresh"); //individual compnents can trap and handle this event as they so wish
                $('body').trigger(event);
            },
            createdRow: function (row, data, index) {
                //add class to row for ease of selection later
                var recordId = index;
                try {
                    recordId = data.record_id
                } catch (err) {
                }

                $(row).addClass(tableID + recordId);
            },
            dom: 'Bfr<"row"><"row info-rw" i>tlp',
        });

        table
            .buttons()
            .nodes()
            .each(function (value) {
                $(this)
                    .removeClass("btn btn-default")
                    .addClass('tiny ui basic button');
            });

        place_task_buttons(componentMeta); //this will place custom buttons on the table for executing tasks on records
    }

    $('#' + tableID + '_wrapper')
        .find(".dataTables_filter")
        .find("input")
        .removeClass("input-sm")
        .attr("placeholder", "Search " + componentMeta.title)
        .attr("size", 30);

} //end of func


function refresh_sub_table(componentMeta, columns) {
    var tableID = componentMeta.tableID;
    var table = $('#' + tableID).DataTable();
    // handle opening and closing summary details
    $('#' + tableID + ' tbody')
        .off('click', 'td.summary-details-control')
        .on('click', 'td.summary-details-control', function (event) {
            event.preventDefault();

            var event = jQuery.Event("posttablerefresh"); //individual compnents can trap and handle this event as they so wish
            $('body').trigger(event);

            var tr = $(this).closest('tr');
            var row = table.row(tr);

            //close other rows
            $('#' + tableID + ' tbody').find('tr').each(function () {

                var row_all = table.row($(this));

                if (row_all.child.isShown()) {
                    // This row is already open - close it
                    if (row_all.data().record_id != row.data().record_id) {
                        row_all.child('');
                        row_all.child.hide();
                        $(this).removeClass('shown');
                    }
                }
            });

            if (row.child.isShown()) {
                // This row is already open - close it
                row.child('');
                row.child.hide();
                tr.removeClass('shown');
            } else {
                // expand row

                var contentHtml = $('<table/>', {
                    // cellpadding: "5",
                    cellspacing: "0",
                    border: "0",
                    // style: "padding-left:50px;"
                });


                columns.forEach(function (col, idx) {
                    if (col.visible || col.data == 'record_id' || col.data == null) { //skip already shown columns
                        return false;
                    }

                    var colTR = $('<tr/>')
                    var colTitle = $('<td/>').append(col.title);
                    var colData = $('<td/>').append(deconvulate_column_data(row.data()[col.data], row.data().record_id + "_" + idx));
                    colTR
                        .append(colTitle)
                        .append(colData);
                    contentHtml.append(colTR);
                });

                //these components require look-up for extra attributes before display
                if (componentMeta.component == "sample" || componentMeta.component == "datafile") {
                    do_component_attributes(componentMeta.component, row.data().record_id, contentHtml, tr, row);
                } else {
                    contentHtml.find("tbody > tr").css("background-color", "rgba(229, 239, 255, 0.3)");
                    row.child($('<div></div>').append(contentHtml).html()).show();
                    tr.addClass('shown');
                }
            }
        });
}

function do_component_attributes(component, targetID, contentHtml, tr, row) {
    var loaderHTML = "<div style='text-align: center'><i class='fa fa-spinner fa-pulse fa-2x'></i></div>";

    var colTR = $('<tr/>')
    var colLoader = $('<td/>').attr('colspan', 2);
    colLoader.append(loaderHTML);
    colTR.append(colLoader)
    contentHtml.append(colTR);

    var task = "attributes_display"; //sample and datafile are resolved differently, call relavant task
    if (component == "datafile") {
        task = "description_summary";
    }

    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'task': task,
            'component': component,
            'target_id': targetID
        },
        success: function (data) {
            var table = Object();
            if (component == "datafile") {
                table = build_description_display(data);
            } else {
                table = build_attributes_display(data);
            }

            table.find("tbody > tr").each(function (indx, dtr) {
                contentHtml.append(dtr);
            });

            colTR.remove();

            contentHtml.find("tbody > tr").css("background-color", "rgba(229, 239, 255, 0.3)");

            row.child($('<div></div>').append(contentHtml).html()).show();
            tr.addClass('shown');
        },
        error: function () {
            alert("Couldn't retrieve " + component + " attributes!");
            return '';
        }
    });
}


function load_records(componentMeta) {
    var csrftoken = $.cookie('csrftoken');

    //loader
    var tableLoader = null;
    if ($("#component_table_loader").length) {
        tableLoader = $('<div class="copo-i-loader"></div>');
        $("#component_table_loader").append(tableLoader);
    }

    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'task': 'table_data',
            'component': componentMeta.component
        },
        success: function (data) {
            do_render_component_table(data, componentMeta);
            //remove loader
            if (tableLoader) {
                tableLoader.remove();
            }
        },
        error: function () {
            alert("Couldn't retrieve " + componentMeta.component + " data!");
        }
    });
}